unit UCoachImportCore;
{$IFDEF FPC}{$MODE Delphi}{$ENDIF}
interface
type
  TImportPhase = (ipIdle, ipRunning, ipReady, ipPublishing, ipPublished, ipFailed, ipCancelled);
function ImportAudioSupported(const Name: UTF8String): boolean;
function ImportCanPublish(Phase: TImportPhase; Auditioned: boolean): boolean;
function QuoteImportArgument(const Value: UnicodeString): UnicodeString;
implementation
uses SysUtils;
function ImportAudioSupported(const Name: UTF8String): boolean;
var Ext: string;
begin
  Ext := LowerCase(ExtractFileExt(Name));
  Result := (Ext = '.wav') or (Ext = '.mp3') or (Ext = '.m4a') or
    (Ext = '.flac') or (Ext = '.ogg') or (Ext = '.aac');
end;
function ImportCanPublish(Phase: TImportPhase; Auditioned: boolean): boolean;
begin
  Result := (Phase = ipReady) and Auditioned;
end;
function QuoteImportArgument(const Value: UnicodeString): UnicodeString;
var I, Slashes: integer;
begin
  Result := '"'; Slashes := 0;
  for I := 1 to Length(Value) do
  begin
    if Value[I] = '\' then Inc(Slashes)
    else begin
      if Value[I] = '"' then
        Result := Result + UnicodeString(StringOfChar('\', Slashes * 2 + 1)) + '"'
      else Result := Result + UnicodeString(StringOfChar('\', Slashes)) + Value[I];
      Slashes := 0;
    end;
  end;
  Result := Result + UnicodeString(StringOfChar('\', Slashes * 2)) + '"';
end;
end.
