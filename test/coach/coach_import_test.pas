program coach_import_test;
{$mode Delphi}
{$codepage utf8}
uses SysUtils, UCoachImportCore;
procedure Check(Value: boolean; const Message_: string);
begin
  if not Value then raise Exception.Create(Message_);
end;
begin
  Check(ImportAudioSupported('中文 歌曲.WAV'), 'unicode WAV');
  Check(ImportAudioSupported('a.MP3'), 'MP3');
  Check(not ImportAudioSupported('song.wav.exe'), 'extension masquerade');
  Check(not ImportCanPublish(ipRunning, true), 'running blocks publish');
  Check(not ImportCanPublish(ipReady, false), 'audition required');
  Check(ImportCanPublish(ipReady, true), 'ready and auditioned');
  Check(not ImportCanPublish(ipPublished, true), 'done blocks second click');
  Check(QuoteImportArgument('') = '""', 'empty quoting');
  Check(QuoteImportArgument('a b') = '"a b"', 'space quoting');
  Check(QuoteImportArgument('a"b') = '"a\"b"', 'quote escaping');
  Check(QuoteImportArgument('C:\a b\') = '"C:\a b\\"', 'trailing slash');
  Check(QuoteImportArgument(UTF8Decode('中文 路径')) = UTF8Decode('"中文 路径"'), 'wide argument');
  Writeln('PASS coach_import: audio suffix, explicit audition gate, Unicode Windows argv');
end.
