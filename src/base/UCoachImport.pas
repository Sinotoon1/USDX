unit UCoachImport;
{$IFDEF FPC}{$MODE Delphi}{$ENDIF}
interface
uses SysUtils, Classes, UPath, UCoachImportCore,
  {$IFDEF MSWINDOWS}Windows{$ELSE}Process{$ENDIF};
type
  TImportNote = record StartTime, EndTime: double; Midi: integer; end;
  TCoachImport = class
  private
    {$IFDEF MSWINDOWS}Child: THandle;{$ELSE}Child: TProcess;{$ENDIF}
    StateFile: IPath;
    Publishing: boolean;
    function Running: boolean;
    function FindEngine: boolean;
    procedure Launch(const Action: string; const Arguments: array of UTF8String);
    procedure WriteRequest(const Title, Artist: UTF8String);
  public
    Phase: TImportPhase;
    DetailPhase, ErrorCode, JobID, VocalsFile, SongFile: UTF8String;
    LyricsPreview: UTF8String;
    EngineRoot, PythonFile, OutputRoot: IPath;
    Duration, Coverage: double;
    NoteCount: integer;
    LyricWordCount, LowConfidenceWordCount, FreestyleWordCount: integer;
    Preview: array of TImportNote;
    constructor Create;
    destructor Destroy; override;
    procedure Prepare(const Audio: UTF8String);
    procedure Publish(const Title, Artist: UTF8String);
    procedure Poll;
    procedure Cancel;
    property Busy: boolean read Running;
  end;
function ImportEnvironment(const Name: string): UTF8String;
function PickImportAudio(out FileName: UTF8String): boolean;
implementation
uses Math, FPJSON, JSONParser, UPlatform, UFileSystem
  {$IFDEF MSWINDOWS}, CommDlg{$ENDIF};

{$IFDEF MSWINDOWS}
// FPC 3.2.2's generic CommDlg declaration uses the ANSI pointer alias even
// for this W entry point. Bind the documented wide record ABI explicitly.
function ImportOpenFileName(var Info: TOpenFilenameW): BOOL; stdcall;
  external 'comdlg32.dll' name 'GetOpenFileNameW';
{$ENDIF}

function ImportEnvironment(const Name: string): UTF8String;
{$IFDEF MSWINDOWS}
var Buffer: UnicodeString; N: DWORD;
begin
  SetLength(Buffer, 32768);
  N := GetEnvironmentVariableW(PWideChar(UnicodeString(Name)), PWideChar(Buffer), Length(Buffer));
  if N >= DWORD(Length(Buffer)) then N := 0;
  SetLength(Buffer, N); Result := UTF8Encode(Buffer);
end;
{$ELSE}
begin Result := GetEnvironmentVariable(Name); end;
{$ENDIF}

function PickImportAudio(out FileName: UTF8String): boolean;
{$IFDEF MSWINDOWS}
var Info: TOpenFilenameW; Buffer: array[0..32767] of WideChar; Filter: UnicodeString;
begin
  FillChar(Info, SizeOf(Info), 0); FillChar(Buffer, SizeOf(Buffer), 0);
  Filter := 'Audio'#0'*.wav;*.mp3;*.m4a;*.flac;*.ogg;*.aac'#0#0;
  Info.lStructSize := SizeOf(Info); Info.hwndOwner := GetActiveWindow;
  Info.lpstrFilter := PWideChar(Filter); Info.lpstrFile := @Buffer[0];
  Info.nMaxFile := Length(Buffer);
  Info.Flags := OFN_FILEMUSTEXIST or OFN_PATHMUSTEXIST or OFN_EXPLORER or OFN_NOCHANGEDIR;
  Result := ImportOpenFileName(Info);
  if Result then FileName := UTF8Encode(UnicodeString(PWideChar(@Buffer[0]))) else FileName := '';
end;
{$ELSE}
begin FileName := ''; Result := false; end;
{$ENDIF}

constructor TCoachImport.Create;
var Value: UTF8String;
begin
  inherited Create;
  Phase := ipIdle;
  Value := ImportEnvironment('USDX_IMPORT_SONGS');
  if Value <> '' then OutputRoot := Path(Value).GetAbsolutePath
  else OutputRoot := Platform.GetGameUserPath.Append('songs').GetAbsolutePath;
end;

function TCoachImport.FindEngine: boolean;
var Base, Candidate: IPath; Iter: IFileIterator; Info: TFileInfo; Level: integer;
  Value: UTF8String;
begin
  EngineRoot := nil; PythonFile := nil;
  Value := ImportEnvironment('USDX_COACH_ROOT');
  if Value <> '' then EngineRoot := Path(Value).GetAbsolutePath
  else begin
    Base := Platform.GetExecutionDir.GetParent;
    for Level := 0 to 1 do
    begin
      Iter := FileSystem.FileFind(Base.Append('*'), faDirectory);
      while Iter.HasNext do
      begin
        Info := Iter.Next;
        if (Info.Attr and faDirectory) = 0 then Continue;
        Candidate := Base.Append(Info.Name);
        if Candidate.Append('src/singing_coach/reference.py').Exists then
        begin EngineRoot := Candidate; Break; end;
      end;
      if EngineRoot <> nil then Break;
      Base := Base.GetParent;
    end;
  end;
  Result := (EngineRoot <> nil);
  if not Result then Exit;
  if not EngineRoot.Append('src/singing_coach/reference.py').Exists then Exit(false);
  Value := ImportEnvironment('USDX_COACH_PYTHON');
  if Value <> '' then PythonFile := Path(Value).GetAbsolutePath
  else PythonFile := EngineRoot.Append({$IFDEF MSWINDOWS}'.venv/Scripts/python.exe'{$ELSE}'.venv/bin/python'{$ENDIF});
  Result := PythonFile.Exists;
end;

function TCoachImport.Running: boolean;
{$IFDEF MSWINDOWS}var Code: DWORD;{$ENDIF}
begin
  {$IFDEF MSWINDOWS}
  Result := (Child <> 0) and GetExitCodeProcess(Child, Code) and (Code = STILL_ACTIVE);
  {$ELSE}Result := (Child <> nil) and Child.Running;{$ENDIF}
end;

procedure TCoachImport.Launch(const Action: string; const Arguments: array of UTF8String);
var Script, DataRoot: IPath; Args: array of UTF8String; I: integer; Value: UTF8String;
  {$IFDEF MSWINDOWS}Startup: TStartupInfoW; Info: TProcessInformation; Command: UnicodeString;{$ENDIF}
  procedure Add(const Value_: UTF8String);
  begin SetLength(Args, Length(Args)+1); Args[High(Args)] := Value_; end;
begin
  if Running then Exit;
  {$IFDEF MSWINDOWS}if Child <> 0 then begin CloseHandle(Child); Child := 0; end;
  {$ELSE}FreeAndNil(Child);{$ENDIF}
  if not FindEngine then begin Phase := ipFailed; ErrorCode := 'engine_missing'; Exit; end;
  Script := Platform.GetExecutionDir.GetParent.Append('tools/coach_import.py');
  if not Script.Exists then begin Phase := ipFailed; ErrorCode := 'import_tool_missing'; Exit; end;
  Publishing := Action = 'publish';
  try
    Add(Script.ToUTF8); Add(Action); Add('--coach-root'); Add(EngineRoot.ToUTF8);
    Add('--state'); Add(StateFile.ToUTF8);
    Value := ImportEnvironment('USDX_COACH_DATA');
    if Value <> '' then begin DataRoot := Path(Value).GetAbsolutePath;
      Add('--data-root'); Add(DataRoot.ToUTF8); end;
    for I := Low(Arguments) to High(Arguments) do Add(Arguments[I]);
    {$IFDEF MSWINDOWS}
    Command := QuoteImportArgument(UTF8Decode(PythonFile.ToUTF8));
    for I := 0 to High(Args) do Command := Command + ' ' + QuoteImportArgument(UTF8Decode(Args[I]));
    FillChar(Startup, SizeOf(Startup), 0); Startup.cb := SizeOf(Startup);
    Startup.dwFlags := STARTF_USESHOWWINDOW; Startup.wShowWindow := SW_HIDE;
    UniqueString(Command);
    if not CreateProcessW(nil, PWideChar(Command), nil, nil, false, CREATE_NO_WINDOW,
      nil, nil, Startup, Info) then raise Exception.Create('worker_start_failed');
    CloseHandle(Info.hThread); Child := Info.hProcess;
    {$ELSE}
    Child := TProcess.Create(nil); Child.Executable := PythonFile.ToUTF8;
    for I := 0 to High(Args) do Child.Parameters.Add(Args[I]);
    Child.Options := []; Child.Execute;
    {$ENDIF}
  except
    on E: Exception do begin Phase := ipFailed; ErrorCode := 'worker_start_failed'; end;
  end;
end;

procedure TCoachImport.Prepare(const Audio: UTF8String);
var ID: TGUID; Directory: IPath;
begin
  if Running then Exit;
  if not ImportAudioSupported(Audio) or not Path(Audio).Exists then
  begin Phase := ipFailed; ErrorCode := 'unsupported_audio'; Exit; end;
  CreateGUID(ID);
  Directory := Platform.GetGameUserPath.Append('coach-import/tasks');
  if not Directory.CreateDirectory(true) then begin Phase := ipFailed; ErrorCode := 'state_write_failed'; Exit; end;
  StateFile := Directory.Append('import-' + Copy(GUIDToString(ID), 2, 36) + '.json');
  Phase := ipRunning; DetailPhase := 'starting'; ErrorCode := ''; JobID := ''; SongFile := '';
  VocalsFile := ''; Duration := 0; NoteCount := 0; SetLength(Preview, 0);
  LyricsPreview := ''; LyricWordCount := 0; LowConfidenceWordCount := 0; FreestyleWordCount := 0;
  Launch('prepare', ['--audio', Path(Audio).GetAbsolutePath.ToUTF8]);
end;

procedure TCoachImport.WriteRequest(const Title, Artist: UTF8String);
var Data: TJSONObject; Buffer: UTF8String; Handle: TFileHandle;
begin
  Data := TJSONObject.Create;
  try
    Data.Add('schema_version', 1); Data.Add('title', Title); Data.Add('artist', Artist);
    Data.Add('confirmation', JobID); Buffer := Data.AsJSON;
    Handle := StateFile.SetExtension('.request.json').CreateFile;
    if Handle = TFileHandle(-1) then raise Exception.Create('state_write_failed');
    try
      if FileWrite(Handle, Buffer[1], Length(Buffer)) <> Length(Buffer) then
        raise Exception.Create('state_write_failed');
    finally FileClose(Handle); end;
  finally Data.Free; end;
end;

procedure TCoachImport.Publish(const Title, Artist: UTF8String);
begin
  if Running or (Phase <> ipReady) or (JobID = '') then Exit;
  try WriteRequest(Title, Artist);
  except Phase := ipFailed; ErrorCode := 'state_write_failed'; Exit; end;
  Phase := ipPublishing; DetailPhase := 'publishing'; ErrorCode := '';
  Launch('publish', ['--songs-root', OutputRoot.ToUTF8,
    '--request', StateFile.SetExtension('.request.json').ToUTF8]);
end;

procedure TCoachImport.Cancel;
var Handle: TFileHandle;
begin
  if (StateFile = nil) or not Running or Publishing then Exit;
  Handle := StateFile.SetExtension('.cancel').CreateFile;
  if Handle <> TFileHandle(-1) then FileClose(Handle);
end;

procedure TCoachImport.Poll;
var Handle: TFileHandle; Stream: THandleStream; Buffer: UTF8String;
  Data: TJSONData; Obj: TJSONObject; Status: string; Notes, Note: TJSONData; I: integer;
begin
  if StateFile = nil then Exit;
  Data := nil;
  if StateFile.Exists then
  try
    Handle := StateFile.Open(fmOpenRead or fmShareDenyNone);
    if Handle = TFileHandle(-1) then raise Exception.Create('state_read_failed');
    Stream := THandleStream.Create(Handle);
    try
      if (Stream.Size <= 0) or (Stream.Size > 262144) then raise Exception.Create('invalid_state');
      SetLength(Buffer, Stream.Size); Stream.ReadBuffer(Buffer[1], Length(Buffer));
    finally Stream.Free; FileClose(Handle); end;
    Data := GetJSON(Buffer);
    try
    if not (Data is TJSONObject) then raise Exception.Create('invalid_state');
    Obj := TJSONObject(Data);
    if (Obj.Get('schema_version', 0) <> 1) or
      (Obj.Get('task_id', '') <> StateFile.GetName.SetExtension('').ToUTF8) then raise Exception.Create('invalid_state');
    Status := Obj.Get('status', ''); DetailPhase := Obj.Get('phase', '');
    // A just-started publish may still see the previous ready snapshot.
    if Publishing and Running and (Status = 'ready') then Exit;
    ErrorCode := Obj.Get('error_code', '');
    if Status = 'ready' then Phase := ipReady
    else if Status = 'published' then Phase := ipPublished
    else if Status = 'failed' then Phase := ipFailed
    else if Status = 'cancelled' then Phase := ipCancelled
    else if Status = 'running' then
      if DetailPhase = 'publishing' then Phase := ipPublishing else Phase := ipRunning;
    if Phase in [ipReady, ipPublished] then
    begin
      JobID := Obj.Get('job_id', ''); VocalsFile := Obj.Get('vocals_path', '');
      SongFile := Obj.Get('song_file', '');
      Duration := Obj.Get('duration_seconds', 0.0); Coverage := Obj.Get('voiced_coverage', 0.0);
      if IsNan(Duration) or IsInfinite(Duration) or (Duration <= 0) or (Duration > 600) or
        IsNan(Coverage) or IsInfinite(Coverage) then raise Exception.Create('invalid_preview');
      NoteCount := Obj.Get('note_count', 0); Notes := Obj.Find('preview');
      LyricsPreview := Obj.Get('lyrics_preview', '');
      LyricWordCount := Obj.Get('lyric_word_count', 0);
      LowConfidenceWordCount := Obj.Get('low_confidence_word_count', 0);
      FreestyleWordCount := Obj.Get('freestyle_word_count', 0);
      if (LyricWordCount <= 0) or (LyricWordCount > 20000) or
        (Length(LyricsPreview) > 800) or (LowConfidenceWordCount < 0) or
        (LowConfidenceWordCount > LyricWordCount) or (FreestyleWordCount < 0) or
        (FreestyleWordCount > LyricWordCount) then raise Exception.Create('invalid_lyrics');
      SetLength(Preview, 0);
      if (Notes is TJSONArray) and (Notes.Count <= 512) then
      begin
        SetLength(Preview, Notes.Count);
        for I := 0 to Notes.Count - 1 do
        begin
          Note := Notes.Items[I];
          if not (Note is TJSONArray) or (Note.Count <> 3) then raise Exception.Create('invalid_preview');
          Preview[I].StartTime := Note.Items[0].AsFloat;
          Preview[I].EndTime := Note.Items[1].AsFloat;
          if IsNan(Preview[I].StartTime) or IsInfinite(Preview[I].StartTime) or
            IsNan(Preview[I].EndTime) or IsInfinite(Preview[I].EndTime) or
            (Preview[I].StartTime < 0) or (Preview[I].EndTime <= Preview[I].StartTime) or
            (Preview[I].EndTime > Duration + 0.01) then raise Exception.Create('invalid_preview');
          Preview[I].Midi := EnsureRange(Note.Items[2].AsInteger, 0, 127);
        end;
      end;
    end;
    finally Data.Free; Data := nil; end;
  except
    if not Running then begin Phase := ipFailed; ErrorCode := 'invalid_state'; end;
  end;
  if not Running and (Phase in [ipRunning, ipPublishing]) then
  begin Phase := ipFailed; ErrorCode := 'worker_exit'; end;
end;

destructor TCoachImport.Destroy;
var Deadline: QWord;
begin
  Cancel; Deadline := GetTickCount64 + 8000;
  while Running and (GetTickCount64 < Deadline) do Sleep(20);
  {$IFDEF MSWINDOWS}
  if Running then TerminateProcess(Child, 1);
  if Child <> 0 then CloseHandle(Child);
  {$ELSE}
  if Running then begin Child.Terminate(1); Child.WaitOnExit(2000); end;
  Child.Free;
  {$ENDIF}
  inherited Destroy;
end;
end.
