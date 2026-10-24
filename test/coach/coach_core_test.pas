program coach_core_test;
{$mode delphi}
uses SysUtils, Math, UCoachCore;
var Samples: array[0..4095] of SmallInt;
    P: TCoachPitch; Gate: TCoachGate; Hint: TCoachHint;
    I, J: Integer; Hz, Offset: Double;
procedure Check(Value: Boolean; const Message: String);
begin
  if not Value then begin Writeln('FAIL ', Message); Halt(1); end;
end;
begin
  Check(CoachMode = cmPlay, 'default is play');
  Check(not CoachMaySaveScores(cmPractice, true), 'practice never saves scores');
  Check(not CoachMaySaveScores(cmPlay, false), 'AUTO never saves scores');
  Check(CoachMaySaveScores(cmPlay, true), 'reviewed play can save');
  for J := -1 to 1 do
  begin
    Offset := J * 70;
    Hz := 440 * Power(2, Offset / 1200);
    for I := 0 to High(Samples) do Samples[I] := Round(10000 * Sin(2*Pi*Hz*I/48000));
    P := CoachDetectPitch(Samples, Length(Samples), 48000);
    Check(P.Valid and (Abs(1200*Log2(P.Hz/Hz)) < 3), 'continuous pitch within 3 cents');
    Gate.Reset;
    for I := 0 to 6 do Hint := Gate.Update(1000+I*40, 1200*Log2(P.Hz/440), true);
    if J < 0 then Check(Hint = chFlat, 'flat');
    if J = 0 then Check(Hint = chClose, 'close');
    if J > 0 then Check(Hint = chSharp, 'sharp');
  end;
  for I := 0 to High(Samples) do
    Samples[I] := Round(3000*Sin(2*Pi*220*I/48000)+12000*Sin(2*Pi*440*I/48000));
  P := CoachDetectPitch(Samples, Length(Samples), 48000);
  Check(P.Valid and (Abs(P.Hz-220)<1), 'dominant second harmonic');
  FillChar(Samples, SizeOf(Samples), 0);
  P := CoachDetectPitch(Samples, Length(Samples), 48000);
  Check(not P.Valid, 'silence rejected');
  RandSeed := 42;
  for I := 0 to High(Samples) do Samples[I] := Random(20000)-10000;
  Check(not CoachDetectPitch(Samples, Length(Samples), 48000).Valid, 'noise rejected');
  Gate.Reset;
  Check(Gate.Update(1000, 70, true) = chWaiting, 'single observation waits');
  Check(Gate.Update(1040, 70, false) = chWaiting, 'rest invalidates history');
  Gate.Reset;
  for I := 0 to 6 do Hint := Gate.Update(1000+I*40, 1200, true);
  Check(Hint = chSharp, 'an octave high is not folded into on-target');
  Check(Gate.Update(2000, 70, true) = chWaiting, 'long gaps reset history');
  Check(not CoachDetectPitch(Samples, 500, 48000).Valid, 'short input rejected');
  Writeln('PASS coach_core: play/practice isolation, +/-70c, harmonic, silence, noise, stability');
end.
