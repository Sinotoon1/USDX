{ SPDX-License-Identifier: GPL-2.0-or-later }
unit UCoachCore;
{$mode delphi}
interface
type
  TCoachMode = (cmPlay, cmPractice);
  TCoachHint = (chWaiting, chFlat, chClose, chSharp);
  TCoachPitch = record
    Valid: Boolean;
    Hz, Confidence: Double;
  end;
  TCoachGate = record
    Values: array[0..6] of Double;
    Count, Cursor: Integer;
    FirstTick, LastTick: Cardinal;
    MedianCents: Double;
    procedure Reset;
    function Update(Tick: Cardinal; Cents: Double; Valid: Boolean): TCoachHint;
  end;
var
  CoachMode: TCoachMode = cmPlay;
  CoachDelayConfirmed: Boolean = false;
function CoachMaySaveScores(Mode: TCoachMode; Reviewed: Boolean): Boolean;
function CoachDetectPitch(const Samples: array of SmallInt; Count: Integer;
  SampleRate: Double): TCoachPitch;
implementation
uses Math;
function CoachMaySaveScores(Mode: TCoachMode; Reviewed: Boolean): Boolean;
begin
  Result := (Mode = cmPlay) and Reviewed;
end;
procedure TCoachGate.Reset;
begin
  Count := 0;
  Cursor := 0;
  FirstTick := 0;
  LastTick := 0;
  MedianCents := 0;
end;
function TCoachGate.Update(Tick: Cardinal; Cents: Double; Valid: Boolean): TCoachHint;
var Sorted: array[0..6] of Double; I, J: Integer; V: Double;
begin
  Result := chWaiting;
  if (not Valid) or IsNan(Cents) or IsInfinite(Cents) then begin Reset; Exit; end;
  if (Count > 0) and ((Tick < LastTick) or (Tick-LastTick > 160)) then Reset;
  if Count = 0 then FirstTick := Tick;
  LastTick := Tick;
  Values[Cursor] := Cents;
  Cursor := (Cursor+1) mod 7;
  Count := Min(7, Count+1);
  if (Count < 4) or (Tick-FirstTick < 160) then Exit;
  for I := 0 to Count-1 do Sorted[I] := Values[I];
  for I := 1 to Count-1 do
  begin
    V := Sorted[I]; J := I-1;
    while (J >= 0) and (Sorted[J] > V) do
    begin Sorted[J+1] := Sorted[J]; Dec(J); end;
    Sorted[J+1] := V;
  end;
  MedianCents := Sorted[Count div 2];
  if MedianCents > 35 then Result := chSharp
  else if MedianCents < -35 then Result := chFlat
  else Result := chClose;
end;
function CoachDetectPitch(const Samples: array of SmallInt; Count: Integer;
  SampleRate: Double): TCoachPitch;
var Data: array[0..4095] of Double;
    Difference: array[0..1024] of Double;
    Step, N, I, Tau, MinTau, MaxTau, Window, Selected, Clipped: Integer;
    Rate, Mean, Energy, Sum, Delta, Refined, Denominator: Double;
begin
  FillChar(Result, SizeOf(Result), 0);
  if (SampleRate < 8000) or (SampleRate > 192000) or
     (Count < 1024) or (Count > Length(Samples)) then Exit;
  Step := Max(1, Trunc(SampleRate/16000));
  N := Min(4096, Count div Step);
  Rate := SampleRate/Step;
  Mean := 0; Clipped := 0;
  for I := 0 to N-1 do
  begin
    Data[I] := Samples[I*Step]/32768;
    Mean := Mean+Data[I];
    if Abs(Data[I]) >= 0.995 then Inc(Clipped);
  end;
  if Clipped > N div 100 then Exit;
  Mean := Mean/N; Energy := 0;
  for I := 0 to N-1 do
  begin Data[I] := Data[I]-Mean; Energy := Energy+Sqr(Data[I]); end;
  if Sqrt(Energy/N) < 0.008 then Exit;
  MinTau := Max(2, Floor(Rate/1100));
  MaxTau := Min(1023, Ceil(Rate/65));
  Window := N-MaxTau;
  if Window < MaxTau then Exit;
  Sum := 0;
  Difference[0] := 1;
  for Tau := 1 to MaxTau do
  begin
    Delta := 0;
    for I := 0 to Window-1 do Delta := Delta+Sqr(Data[I]-Data[I+Tau]);
    Sum := Sum+Delta;
    if Sum > 0 then Difference[Tau] := Delta*Tau/Sum else Difference[Tau] := 1;
  end;
  Selected := -1;
  Tau := MinTau;
  while Tau < MaxTau do
  begin
    if Difference[Tau] < 0.10 then
    begin
      while (Tau+1 < MaxTau) and (Difference[Tau+1] < Difference[Tau]) do Inc(Tau);
      Selected := Tau; Break;
    end;
    Inc(Tau);
  end;
  if Selected < 0 then Exit;
  Refined := Selected;
  Denominator := Difference[Selected-1]-2*Difference[Selected]+Difference[Selected+1];
  if Abs(Denominator) > 1e-12 then
    Refined := Refined+0.5*(Difference[Selected-1]-Difference[Selected+1])/Denominator;
  Result.Hz := Rate/Refined;
  Result.Confidence := 1-Difference[Selected];
  Result.Valid := (Result.Hz >= 65) and (Result.Hz <= 1100) and (Result.Confidence >= 0.90);
end;
end.
