unit UScreenCoachImport;
{$IFDEF FPC}{$MODE Delphi}{$ENDIF}
interface
uses UMenu, UCoachImport, UCoachImportCore, SDL2;
type
  TScreenCoachImport = class(TMenu)
  private
    Importer: TCoachImport;
    AudioFile, SongTitle, Artist, LastJob: UTF8String;
    StatusText, DetailText, SummaryText, Editing: integer;
    Auditioned, Playing, Loaded, Cancelling: boolean;
    LastPoll: cardinal;
    LocalError: UTF8String;
    procedure StopPreview;
    procedure EndEditing;
    procedure DoAction(Index: integer);
    procedure UpdateView;
    procedure DrawCurve;
    procedure Paste;
    function ErrorText(const Code: UTF8String): UTF8String;
  public
    constructor Create; override;
    destructor Destroy; override;
    procedure OnShow; override;
    procedure OnHide; override;
    procedure SetAudioFile(const Value: UTF8String);
    procedure InsertText(const Value: UTF8String);
    function Draw: boolean; override;
    function ParseInput(PressedKey: cardinal; CharCode: UCS4Char; PressedDown: boolean): boolean; override;
    function ParseMouse(MouseButton: integer; BtnDown: boolean; X, Y: integer): boolean; override;
  end;
implementation
uses SysUtils, Math, UGraphic, UThemes, UStudioUI, UMusic, UPath, UPathUtils,
  ULanguage, UUnicodeUtils, UMain, UIMotion, UCommon, URenderer, UText,
  USongs, UCoachCore;

constructor TScreenCoachImport.Create;
var I: integer;
begin
  inherited Create;
  Importer := TCoachImport.Create; Editing := -1; Artist := 'Unknown';
  StatusText := AddText(Theme.CoachImport.TextStatus);
  DetailText := AddText(Theme.CoachImport.TextDetail);
  SummaryText := AddText(Theme.CoachImport.TextSummary);
  LoadFromTheme(Theme.CoachImport);
  for I := 0 to 6 do AddButton(Theme.CoachImport.Buttons[I]);
  Interaction := 0;
end;

destructor TScreenCoachImport.Destroy;
begin
  StopPreview; Importer.Free;
  inherited Destroy;
end;

procedure TScreenCoachImport.OnShow;
var Value: UTF8String;
begin
  inherited;
  SoundLib.PauseBgMusic;
  if AudioFile = '' then
  begin
    Value := ImportEnvironment('USDX_IMPORT_FILE');
    if Value <> '' then SetAudioFile(Value);
  end;
  UpdateView;
end;

procedure TScreenCoachImport.OnHide;
begin
  EndEditing; StopPreview;
  inherited;
end;

procedure TScreenCoachImport.SetAudioFile(const Value: UTF8String);
var Clean: UTF8String; Chars: UCS4String;
begin
  if Importer.Busy then Exit;
  Clean := Trim(Value);
  if (Length(Clean) >= 2) and (Clean[1] = '"') and (Clean[Length(Clean)] = '"') then
    Clean := Copy(Clean, 2, Length(Clean) - 2);
  if not ImportAudioSupported(Clean) or not Path(Clean).Exists then
  begin LocalError := 'unsupported_audio'; UpdateView; Exit; end;
  StopPreview; EndEditing;
  AudioFile := Path(Clean).GetAbsolutePath.ToUTF8;
  SongTitle := Path(AudioFile).GetName.SetExtension('').ToUTF8;
  Chars := UTF8ToUCS4String(SongTitle);
  if Length(Chars) > 120 then begin SetLength(Chars, 120); SongTitle := UCS4ToUTF8String(Chars); end;
  Artist := 'Unknown'; LocalError := ''; Auditioned := false; Loaded := false;
  Cancelling := false; LastJob := ''; Importer.Phase := ipIdle;
  Importer.ErrorCode := ''; Importer.VocalsFile := ''; Importer.SongFile := '';
  SetLength(Importer.Preview, 0); Importer.Duration := 0; Importer.JobID := '';
  UpdateView;
end;

procedure TScreenCoachImport.StopPreview;
begin
  if Playing then begin AudioPlayback.Stop; AudioPlayback.Close; end;
  Playing := false;
end;

procedure TScreenCoachImport.EndEditing;
begin
  if Editing >= 0 then
  begin
    Button[Editing].Text[0].Writable := false;
    Button[Editing].Text[0].Selected := false;
  end;
  Editing := -1; SetTextInput(false);
end;

function TScreenCoachImport.ErrorText(const Code: UTF8String): UTF8String;
var Key: UTF8String;
begin
  Key := 'IMPORT_ERROR_' + UpperCase(Code);
  Result := Language.Translate(Key);
  if Result = Key then Result := Language.Translate('IMPORT_ERROR_GENERIC') + ' ' + Copy(Code, 1, 160);
end;

procedure TScreenCoachImport.InsertText(const Value: UTF8String);
var Current: UTF8String; Chars: UCS4String; I: integer;
begin
  if Editing < 0 then Exit;
  if Editing = 1 then Current := SongTitle else Current := Artist;
  Chars := UTF8ToUCS4String(Value);
  for I := 0 to High(Chars) do
    if (Chars[I] >= 32) and (Length(UTF8ToUCS4String(Current)) < 120) then
      Current := Current + UCS4ToUTF8String(Chars[I]);
  if Editing = 1 then SongTitle := Current else Artist := Current;
  UpdateView;
end;

procedure TScreenCoachImport.Paste;
var Raw: PAnsiChar; Value: UTF8String;
begin
  Raw := SDL_GetClipboardText;
  if Raw = nil then Exit;
  try Value := UTF8String(Raw); finally SDL_free(Raw); end;
  if Editing < 0 then SetAudioFile(Value)
  else begin
    Value := StringReplace(StringReplace(Value, #13, ' ', [rfReplaceAll]), #10, ' ', [rfReplaceAll]);
    if Length(UTF8ToUCS4String(Value)) > 120 then Exit;
    if Editing = 1 then SongTitle := Value else Artist := Value;
    UpdateView;
  end;
end;

procedure TScreenCoachImport.DoAction(Index: integer);
var FileName: UTF8String;
begin
  case Index of
    0: if not Importer.Busy then
      begin
        if PickImportAudio(FileName) then SetAudioFile(FileName)
        {$IFNDEF MSWINDOWS}else LocalError := 'choose_or_paste'{$ENDIF};
      end;
    1, 2: if not Importer.Busy then
      begin EndEditing; Editing := Index; SetTextInput(true);
        Button[Editing].Text[0].Writable := true; Button[Editing].Text[0].Selected := true; end;
    3: if not Importer.Busy then
      begin
        if (Importer.Phase = ipPublished) and Loaded then
          ScreenMain.StartCoach(cmPractice)
        else if AudioFile <> '' then
        begin StopPreview; Auditioned := false; LastJob := ''; LocalError := '';
          Loaded := false; Cancelling := false; Importer.Prepare(AudioFile); end;
      end;
    4: if (Importer.Phase = ipReady) and not Importer.Busy then
      begin
        if Playing then StopPreview
        else if AudioPlayback.Open(Path(Importer.VocalsFile), PATH_NONE) then
        begin AudioPlayback.Play; Playing := true; Auditioned := true; end
        else LocalError := 'audition_failed';
      end;
    5: if ImportCanPublish(Importer.Phase, Auditioned) and not Importer.Busy then
      begin StopPreview; LocalError := ''; Importer.Publish(SongTitle, Artist); end;
    6: if Importer.Busy then
      begin
        if Importer.Phase <> ipPublishing then begin Importer.Cancel; Cancelling := true; end;
      end
      else FadeTo(@ScreenMain, SoundLib.Back);
  end;
  UpdateView;
end;

procedure TScreenCoachImport.UpdateView;
var StatusKey, DetailKey, Error: UTF8String; I: integer; Busy_: boolean;
begin
  Busy_ := Importer.Busy;
  StatusKey := 'IMPORT_IDLE'; DetailKey := 'IMPORT_IDLE_HINT';
  case Importer.Phase of
    ipRunning: begin StatusKey := 'IMPORT_' + UpperCase(Importer.DetailPhase);
      DetailKey := 'IMPORT_RUNNING_HINT'; end;
    ipReady: begin StatusKey := 'IMPORT_READY'; DetailKey := 'IMPORT_READY_HINT'; end;
    ipPublishing: begin StatusKey := 'IMPORT_PUBLISHING'; DetailKey := 'IMPORT_RUNNING_HINT'; end;
    ipPublished: begin StatusKey := 'IMPORT_DONE'; DetailKey := 'IMPORT_DONE_HINT'; end;
    ipFailed: begin StatusKey := 'IMPORT_FAILED'; DetailKey := 'IMPORT_RETRY_HINT'; end;
    ipCancelled: begin StatusKey := 'IMPORT_CANCELLED'; DetailKey := 'IMPORT_RETRY_HINT'; end;
  end;
  if Cancelling and Busy_ then StatusKey := 'IMPORT_CANCELLING';
  Text[StatusText].Text := Language.Translate(StatusKey);
  Text[DetailText].Text := Language.Translate(DetailKey);
  Error := Importer.ErrorCode;
  if LocalError <> '' then Error := LocalError;
  if Error <> '' then Text[DetailText].Text := ErrorText(Error);
  Text[SummaryText].Text := '';
  if Importer.Phase in [ipReady, ipPublished] then
    Text[SummaryText].Text := Format(Language.Translate('IMPORT_SUMMARY'),
      [Importer.Duration, Importer.NoteCount, Importer.Coverage * 100]);
  if AudioFile = '' then Button[0].Text[0].Text := Language.Translate('IMPORT_FILE')
  else Button[0].Text[0].Text := Path(AudioFile).GetName.ToUTF8;
  Button[1].Text[0].Text := SongTitle; Button[2].Text[0].Text := Artist;
  Button[3].Text[0].Text := Language.Translate('IMPORT_ANALYZE');
  if (Importer.Phase = ipPublished) and Loaded then Button[3].Text[0].Text := Language.Translate('IMPORT_LIBRARY');
  Button[4].Text[0].Text := Language.Translate('IMPORT_LISTEN');
  if Playing then Button[4].Text[0].Text := Language.Translate('IMPORT_STOP');
  Button[6].Text[0].Text := Language.Translate('IMPORT_BACK');
  if Busy_ then Button[6].Text[0].Text := Language.Translate('IMPORT_CANCEL');
  for I := 0 to 3 do Button[I].Selectable := not Busy_;
  Button[3].Selectable := not Busy_ and (AudioFile <> '');
  Button[4].Selectable := not Busy_ and (Importer.Phase = ipReady);
  Button[5].Selectable := not Busy_ and ImportCanPublish(Importer.Phase, Auditioned) and (Trim(SongTitle) <> '');
  Button[6].Selectable := not Busy_ or (Importer.Phase <> ipPublishing);
end;

procedure TScreenCoachImport.DrawCurve;
var I, LowNote, HighNote: integer; X, Y, W, Head: single; Ink, Muted: TRGB;
begin
  Ink := StudioColor('StudioAccent'); Muted := StudioColor('StudioMuted');
  if (Length(Importer.Preview) > 0) and (Importer.Duration > 0) then
  begin
    LowNote := 127; HighNote := 0;
    for I := 0 to High(Importer.Preview) do
    begin LowNote := Min(LowNote, Importer.Preview[I].Midi); HighNote := Max(HighNote, Importer.Preview[I].Midi); end;
    for I := 0 to High(Importer.Preview) do
    begin
      X := 52 + 696 * EnsureRange(Importer.Preview[I].StartTime / Importer.Duration, 0.0, 1.0);
      W := Max(1, 696 * (Importer.Preview[I].EndTime - Importer.Preview[I].StartTime) / Importer.Duration);
      Y := 478 - 30 * (Importer.Preview[I].Midi - LowNote) / Max(1, HighNote - LowNote);
      StudioRoundRect(X, Y, 0.2, Min(W, 748-X), 3, 1, Ink, 1);
    end;
    if Playing then
    begin
      Head := 52 + 696 * EnsureRange(AudioPlayback.Position / Importer.Duration, 0.0, 1.0);
      Renderer.DrawLine(Head, 444, Head, 482, 0.3, 1.5, Muted.R, Muted.G, Muted.B, 1);
    end;
  end
  else begin
    SetFontFamily(0); SetFontStyle(ftRegular); SetFontSize(16); SetFontReflection(false, 0);
    SetFontItalic(false); SetFontZ(0.3); SetFontPos(56, 452);
    SetFontColor(Muted.R, Muted.G, Muted.B, 1); PrintText(Language.Translate('IMPORT_EMPTY_CURVE'));
  end;
end;

function TScreenCoachImport.Draw: boolean;
begin
  if ElapsedTicks(SDL_GetTicks, LastPoll) >= 250 then
  begin
    LastPoll := SDL_GetTicks;
    if Importer.Busy or (Importer.Phase in [ipRunning, ipPublishing]) then Importer.Poll;
    if (Importer.JobID <> LastJob) then begin LastJob := Importer.JobID; Auditioned := false; end;
    if not Importer.Busy then Cancelling := false;
    if (Importer.Phase = ipPublished) and not Loaded then
    begin
      AddSongPath(Importer.OutputRoot);
      Loaded := Songs.AddImportedSong(Path(Importer.SongFile));
      if not Loaded then LocalError := 'library_load_failed';
    end;
    if Playing and AudioPlayback.Finished then StopPreview;
    UpdateView;
  end;
  Result := inherited Draw;
  DrawCurve;
end;

function TScreenCoachImport.ParseMouse(MouseButton: integer; BtnDown: boolean; X, Y: integer): boolean;
begin
  if (MouseButton = SDL_BUTTON_LEFT) and not BtnDown then EndEditing;
  Result := inherited ParseMouse(MouseButton, BtnDown, X, Y);
end;

function TScreenCoachImport.ParseInput(PressedKey: cardinal; CharCode: UCS4Char; PressedDown: boolean): boolean;
var Value: UTF8String; Chars: UCS4String;
begin
  Result := true;
  if not PressedDown then Exit;
  if (PressedKey = SDLK_v) and ((SDL_GetModState and KMOD_CTRL) <> 0) then begin Paste; Exit; end;
  if Editing >= 0 then
  begin
    if PressedKey in [SDLK_RETURN, SDLK_ESCAPE] then begin EndEditing; Exit; end;
    if Editing = 1 then Value := SongTitle else Value := Artist;
    if (PressedKey = SDLK_a) and ((SDL_GetModState and KMOD_CTRL) <> 0) then Value := ''
    else if PressedKey = SDLK_BACKSPACE then
    begin Chars := UTF8ToUCS4String(Value); if Length(Chars) > 0 then SetLength(Chars, Length(Chars)-1);
      Value := UCS4ToUTF8String(Chars); end
    else if (CharCode >= 32) and (Length(UTF8ToUCS4String(Value)) < 120) then
      Value := Value + UCS4ToUTF8String(CharCode);
    if Editing = 1 then SongTitle := Value else Artist := Value;
    UpdateView; Exit;
  end;
  case PressedKey of
    SDLK_ESCAPE, SDLK_BACKSPACE: DoAction(6);
    SDLK_RETURN: DoAction(Interaction);
    SDLK_F7: DoAction(3);
    SDLK_UP: InteractDec;
    SDLK_DOWN: InteractInc;
    SDLK_LEFT: InteractPrev;
    SDLK_RIGHT: InteractNext;
  end;
end;
end.
