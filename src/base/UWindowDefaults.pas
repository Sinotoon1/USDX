unit UWindowDefaults;

{$IFDEF FPC}
  {$MODE Delphi}
{$ENDIF}

interface

procedure GetDefaultWindowSize(UsableWidth, UsableHeight: integer;
  out Width, Height: integer);

implementation

procedure GetDefaultWindowSize(UsableWidth, UsableHeight: integer;
  out Width, Height: integer);
const
  FrameAllowance = 64;
var
  Units: integer;
begin
  if (UsableWidth <= 0) or (UsableHeight <= 0) then
  begin
    Width := 800;
    Height := 600;
    Exit;
  end;

  // Keep the native 800x600 canvas undistorted. Reserve room for window
  // decorations inside the usable desktop (which already excludes taskbars).
  Units := 320; // 1280x960 maximum, including on high-resolution displays
  if (UsableWidth - FrameAllowance) div 4 < Units then
    Units := (UsableWidth - FrameAllowance) div 4;
  if (UsableHeight - FrameAllowance) div 3 < Units then
    Units := (UsableHeight - FrameAllowance) div 3;
  if Units < 1 then
    Units := 1;
  Width := Units * 4;
  Height := Units * 3;
end;

end.
