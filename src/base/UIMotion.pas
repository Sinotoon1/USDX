unit UIMotion;
{$IFDEF FPC}{$MODE Delphi}{$ENDIF}

interface

type
  TUIMotion = record
    StartValue, Target: double;
    StartedAt, Duration: cardinal;
  end;
  TUIPointer = record
    Captured: integer;
  end;

function ElapsedTicks(NowTick, StartTick: cardinal): cardinal;
function SmoothProgress(Value: double): double;
function MotionValue(const Motion: TUIMotion; NowTick: cardinal): double;
procedure RetargetMotion(var Motion: TUIMotion; Target: double;
  NowTick, DurationMs: cardinal);
procedure PointerDown(var Pointer: TUIPointer; Hit: integer);
function PointerUp(var Pointer: TUIPointer; Hit: integer): integer;
procedure CancelPointer(var Pointer: TUIPointer);

implementation

function ElapsedTicks(NowTick, StartTick: cardinal): cardinal;
begin
  if NowTick >= StartTick then
    Result := NowTick - StartTick
  else
    Result := cardinal(QWord(High(cardinal)) - StartTick + 1 + NowTick);
end;

function SmoothProgress(Value: double): double;
begin
  if Value <= 0 then Result := 0
  else if Value >= 1 then Result := 1
  else Result := Value * Value * (3 - 2 * Value);
end;

function MotionValue(const Motion: TUIMotion; NowTick: cardinal): double;
var
  Elapsed: cardinal;
begin
  Elapsed := ElapsedTicks(NowTick, Motion.StartedAt);
  if (Motion.Duration = 0) or (Elapsed >= Motion.Duration) then
    Result := Motion.Target
  else
    Result := Motion.StartValue + (Motion.Target - Motion.StartValue) *
      SmoothProgress(Elapsed / Motion.Duration);
end;

procedure RetargetMotion(var Motion: TUIMotion; Target: double;
  NowTick, DurationMs: cardinal);
begin
  if DurationMs = 0 then
    Motion.StartValue := Target
  else
  begin
    if Motion.Target = Target then Exit;
    Motion.StartValue := MotionValue(Motion, NowTick);
  end;
  Motion.Target := Target;
  Motion.StartedAt := NowTick;
  Motion.Duration := DurationMs;
end;

procedure PointerDown(var Pointer: TUIPointer; Hit: integer);
begin
  Pointer.Captured := Hit;
end;

function PointerUp(var Pointer: TUIPointer; Hit: integer): integer;
begin
  Result := -1;
  if (Hit >= 0) and (Hit = Pointer.Captured) then Result := Hit;
  CancelPointer(Pointer);
end;

procedure CancelPointer(var Pointer: TUIPointer);
begin
  Pointer.Captured := -1;
end;

end.
