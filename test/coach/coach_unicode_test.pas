program coach_unicode_test;
{$mode Delphi}
{$codepage UTF8}
uses {$ifdef unix}cwstring,{$endif} SysUtils, UUnicodeUtils;
var S: UTF8String;
begin
  try
    S := TransliterateToASCII('中文验收');
    if S <> 'ZhongWenYanShou' then Halt(1);
    if TransliterateToASCII('Known A4 target') <> 'Known A4 target' then Halt(1);
    WriteLn('TRANSLITERATED=', S);
    WriteLn('PASS coach_unicode: Chinese song title indexing');
  except
    on E: Exception do begin
      WriteLn(E.ClassName, ': ', E.Message);
      DumpExceptionBacktrace(Output);
      Halt(1);
    end;
  end;
end.
