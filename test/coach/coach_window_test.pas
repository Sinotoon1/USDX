program coach_window_test;

{$MODE Delphi}

uses UWindowDefaults;

procedure Check(UsableW, UsableH, ExpectedW, ExpectedH: integer);
var
  W, H: integer;
begin
  GetDefaultWindowSize(UsableW, UsableH, W, H);
  if (W <> ExpectedW) or (H <> ExpectedH) then
  begin
    WriteLn('FAIL window: usable=', UsableW, 'x', UsableH,
      '; actual=', W, 'x', H, '; expected=', ExpectedW, 'x', ExpectedH);
    Halt(1);
  end;
end;

var
  UsableW, UsableH, W, H: integer;
begin
  Check(1920, 1032, 1280, 960); // current Windows working area
  Check(1920, 1080, 1280, 960);
  Check(3840, 2160, 1280, 960);
  Check(1366, 728, 884, 663);
  Check(1024, 768, 936, 702);
  Check(800, 600, 712, 534);
  Check(64, 64, 4, 3);
  Check(0, 0, 800, 600); // unavailable SDL metrics
  Check(-1, 1080, 800, 600);
  Check(High(integer), High(integer), 1280, 960);

  UsableW := 128;
  while UsableW <= 4096 do
  begin
    UsableH := 128;
    while UsableH <= 2160 do
    begin
      GetDefaultWindowSize(UsableW, UsableH, W, H);
      if (W < 4) or (H < 3) or (W > 1280) or (H > 960) or
         (W > UsableW - 64) or (H > UsableH - 64) or (W * 3 <> H * 4) then
      begin
        WriteLn('FAIL window: fit/aspect invariant');
        Halt(1);
      end;
      Inc(UsableH, 17);
    end;
    Inc(UsableW, 23);
  end;
  WriteLn('PASS coach_window: 1280x960 cap, small-screen fit, 4:3, metrics fallback');
end.
