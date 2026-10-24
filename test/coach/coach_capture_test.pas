program coach_capture_test;
{$mode delphi}
uses
  {$ifdef unix}cthreads,{$endif}
  Classes, SysUtils, Math, SDL2, URecord, UMusic, UIni, UCoachCore, UCommandLine, UNote,
  ULog, UPath, UPathUtils;
var
  Buffer: TCaptureBuffer;
  Device: TAudioInputDevice;
  Input: TAudioInputBase;
  Samples: array[0..4095] of SmallInt;
  SavedSamples: array[0..4095] of SmallInt;
  RecordingDir: String;
  Wave: TFileStream;
  Rate: Cardinal;
  I: Integer;
procedure Check(Value: Boolean; const Message: String);
begin
  if not Value then begin Writeln('FAIL ', Message); Halt(1); end;
end;
type
  TTestInputDevice = class(TAudioInputDevice)
    AllowStart: Boolean;
    function Start: Boolean; override;
    function Stop: Boolean; override;
    function GetVolume: System.Single; override;
    procedure SetVolume(Volume: System.Single); override;
  end;
  TTestInput = class(TAudioInputBase)
    function GetName: String; override;
    function InitializeRecord(ScanMode: TAudioInputScanMode): Boolean; override;
  end;
function TTestInputDevice.Start: Boolean;
begin Result := AllowStart; end;
function TTestInputDevice.Stop: Boolean;
begin Result := true; end;
function TTestInputDevice.GetVolume: System.Single;
begin Result := 1; end;
procedure TTestInputDevice.SetVolume(Volume: System.Single);
begin end;
function TTestInput.GetName: String;
begin Result := 'capture regression fixture'; end;
function TTestInput.InitializeRecord(ScanMode: TAudioInputScanMode): Boolean;
begin Result := true; end;
begin
  SDL_Init(SDL_INIT_TIMER);
  Ini := TIni.Create;
  Params := TCMDParams.Create;
  Params.Debug := false;
  Log := TLog.Create;
  RecordingDir := IncludeTrailingPathDelimiter(GetTempDir) +
    'usdx-capture-' + IntToStr(GetTickCount64) + PathDelim;
  ForceDirectories(RecordingDir);
  LogPath := Path(RecordingDir);
  Buffer := TCaptureBuffer.Create;
  Device := TTestInputDevice.Create;
  Input := TTestInput.Create;
  try
    Ini.ThresholdIndex := 0;
    CoachMode := cmPractice;
    SDL_Delay(45);
    Check(not Assigned(Buffer.AudioFormat), 'fresh player has no capture format');
    Buffer.AnalyzeBuffer;
    Check(not Buffer.ToneValid and not Buffer.CoachPitch.Valid,
      'missing microphone produces no pitch');
    Writeln('PASS no microphone: AnalyzeBuffer returns without format or pitch');
    Log.LogVoice(0);
    Check(not FileExists(RecordingDir+'Voice0001.wav'),
      'no microphone saves no invented recording');
    CoachMode := cmPlay;
    Buffer.AnalyzeBuffer;
    Check(not Buffer.ToneValid, 'play mode also tolerates no input');

    Device.AudioFormat := TAudioFormatInfo.Create(1, 44100, asfS16);
    SetLength(Device.CaptureChannel, 1);
    Device.LinkCaptureBuffer(0, Buffer);
    Check(Assigned(Buffer.AudioFormat), 'assigned input supplies a format');
    for I := 0 to High(Buffer.AnalysisBuffer) do
      Buffer.AnalysisBuffer[I] := Round(12000*Sin(2*Pi*440*I/44100));
    CoachMode := cmPlay;
    Buffer.AnalyzeBuffer;
    Check(Buffer.ToneValid, 'connected input still detects a tone');
    Writeln('PASS connected input: 440 Hz detected');

    Buffer.CoachPitch.Valid := true;
    Buffer.CoachPitch.Hz := 440;
    Buffer.Clear;
    Check(not Buffer.ToneValid and not Buffer.CoachPitch.Valid,
      'new song clears old pitch validity');
    Device.LinkCaptureBuffer(0, nil);
    Check(not Buffer.CaptureActive, 'stopped input is inactive');
    CoachMode := cmPractice;
    SDL_Delay(45);
    Buffer.AnalyzeBuffer;
    Check(not Buffer.ToneValid and not Buffer.CoachPitch.Valid,
      'disconnected input never reuses a stale pitch');
    Writeln('PASS disconnected input: inactive, no stale tone or coach pitch');

    // The device was enumerated/configured but opening it now fails.
    PlayersPlay := 1;
    SetLength(AudioInputProcessor.DeviceList, 1);
    AudioInputProcessor.DeviceList[0] := Device;
    SetLength(Ini.InputDeviceConfig, 1);
    SetLength(Ini.InputDeviceConfig[0].ChannelToPlayerMap, 1);
    Ini.InputDeviceConfig[0].ChannelToPlayerMap[0] := 1;
    Device.CfgIndex := 0;
    Input.CaptureStart;
    Check(not Assigned(Device.CaptureChannel[0]), 'failed start unlinks the channel');
    Check(not AudioInputProcessor.Sound[0].CaptureActive,
      'failed start leaves no active capture');
    AudioInputProcessor.Sound[0].AnalyzeBuffer;
    Check(not AudioInputProcessor.Sound[0].CoachPitch.Valid,
      'failed start never supplies a pitch');
    Writeln('PASS device open failure: capture channel and pitch stay unavailable');

    TTestInputDevice(Device).AllowStart := true;
    Input.CaptureStart;
    for I := 0 to High(Samples) do
      Samples[I] := Round(12000*Sin(2*Pi*440*I/44100));
    Ini.SavePlayback := 1;
    SDL_Delay(45);
    AudioInputProcessor.HandleMicrophoneData(PByteArray(@Samples[0]), SizeOf(Samples), Device);
    AudioInputProcessor.Sound[0].AnalyzeBuffer;
    Check(AudioInputProcessor.Sound[0].CoachPitch.Valid and
      (Abs(AudioInputProcessor.Sound[0].CoachPitch.Hz-440) < 2),
      'a successful retry resumes fresh practice pitch detection');
    Input.CaptureStop;
    Check(AudioInputProcessor.Sound[0].LogBuffer.Size = SizeOf(Samples),
      'stopping preserves the recording for Finish/LogVoice');
    Check(Assigned(AudioInputProcessor.Sound[0].AudioFormat),
      'recording format remains available to LogVoice after stop');
    Log.LogVoice(0);
    Wave := TFileStream.Create(RecordingDir+'Voice0001.wav', fmOpenRead);
    try
      Check(Wave.Size = 44+SizeOf(Samples), 'saved WAV includes all recorded samples');
      Wave.Position := 24;
      Wave.ReadBuffer(Rate, SizeOf(Rate));
      Check(Rate = 44100, 'saved WAV retains capture sample rate');
      Wave.Position := 44;
      Wave.ReadBuffer(SavedSamples[0], SizeOf(SavedSamples));
      Check(CompareMem(@SavedSamples[0], @Samples[0], SizeOf(Samples)),
        'saved WAV retains the actual PCM bytes');
    finally
      Wave.Free;
    end;
    Check(not AudioInputProcessor.Sound[0].CaptureActive and
      not AudioInputProcessor.Sound[0].CoachPitch.Valid,
      'capture stop invalidates all input state');
    Writeln('PASS retry: real PCM buffer detects 440 Hz; stopping clears pitch');
    AudioInputProcessor.Sound[0].Clear;
    Check(AudioInputProcessor.Sound[0].LogBuffer.Size = 0,
      'starting a new session clears the old recording');
    Writeln('PASS recording: stopped capture saves exact 44100 Hz WAV; next session clears it');
    SetLength(AudioInputProcessor.DeviceList, 0);
  finally
    Input.Free;
    Device.Free;
    Buffer.Free;
    FreeAndNil(Params);
    FreeAndNil(Log);
    FreeAndNil(Ini);
    SDL_Quit;
  end;
end.
