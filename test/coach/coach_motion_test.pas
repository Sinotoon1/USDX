program coach_motion_test;
{$MODE Delphi}
uses SysUtils, UIMotion;

procedure Check(Value: boolean; const Message: string);
begin
  if not Value then begin WriteLn('FAIL coach_motion: ', Message); Halt(1); end;
end;

var
  M: TUIMotion;
  P: TUIPointer;
  V, Before: double;
  I, Step: integer;
begin
  FillChar(M, SizeOf(M), 0);
  RetargetMotion(M, 1, 1000, 160);
  Check(MotionValue(M, 1000) = 0, 'start');
  Check(Abs(MotionValue(M, 1080) - 0.5) < 0.00001, 'midpoint');
  Check(MotionValue(M, 1160) = 1, 'end');
  Check(MotionValue(M, 9000) = 1, 'stall catches up');
  Before := MotionValue(M, 1080);
  RetargetMotion(M, 0, 1080, 160);
  Check(Abs(MotionValue(M, 1080)-Before)<0.00001, 'reversal is continuous');
  Check(MotionValue(M, 1240) = 0, 'reversal ends');
  RetargetMotion(M, 1, 2000, 0);
  Check(MotionValue(M, 2000) = 1, 'reduced motion immediate');
  FillChar(M, SizeOf(M), 0);
  RetargetMotion(M, 1, High(cardinal)-79, 160);
  Check(Abs(MotionValue(M, 0)-0.5)<0.00001, 'SDL tick wrap midpoint');
  Check(MotionValue(M, 80)=1, 'SDL tick wrap end');
  for Step := 7 to 33 do
  begin
    FillChar(M, SizeOf(M), 0);
    RetargetMotion(M, 1, 1000, 160);
    Before := 0;
    I := 0;
    while I <= 400 do
    begin
      V := MotionValue(M, 1000+cardinal(I));
      Check((V>=Before) and (V>=0) and (V<=1), 'monotonic at variable frame rate');
      Before := V;
      Inc(I, Step);
    end;
    Check(MotionValue(M, 1400)=1, 'same final state at any FPS');
  end;
  CancelPointer(P);
  Check(PointerUp(P, 2)=-1, 'release without press');
  PointerDown(P, 2);
  Check(PointerUp(P, 2)=2, 'same target activates');
  Check(PointerUp(P, 2)=-1, 'one activation only');
  PointerDown(P, 2);
  Check(PointerUp(P, -1)=-1, 'release outside cancels');
  PointerDown(P, 2);
  Check(PointerUp(P, 3)=-1, 'release on other target cancels');
  PointerDown(P, 2); CancelPointer(P);
  Check(PointerUp(P, 2)=-1, 'hide/focus loss cancels');
  Check(ElapsedTicks(10, High(cardinal)-9)=20, 'elapsed wraps without overflow');
  WriteLn('PASS coach_motion: time-based, reversal, reduced motion, tick wrap, FPS, press/release/cancel');
end.
