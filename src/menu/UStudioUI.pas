unit UStudioUI;
{$IFDEF FPC}{$MODE Delphi}{$ENDIF}

interface

uses UCommon, URenderer;

function StudioColor(const Name: string): TRGB;
function StudioDuration(DurationMs: cardinal): cardinal;
function StudioPageProgress(NowTick, StartTick, DurationMs: cardinal): double;
procedure StudioRoundRect(X, Y, Z, W, H, Radius: single; const Color: TRGB; Alpha: single);
procedure StudioButton(const Texture: TTexture; const Normal, Hover: TRGB;
  Focus, Press: single; Enabled: boolean);
procedure StudioSelector(const Texture, Values: TTexture; Focus: single; Arrows: boolean);
procedure StudioShell;

implementation

uses Math, UThemes, UIni, UIMotion, UText, ULanguage;

function StudioColor(const Name: string): TRGB;
var
  Index: integer;
begin
  Index := ColorExists(Name);
  if Index >= 0 then Result := UThemes.Color[Index].RGB
  else begin Result.R := 0; Result.G := 0; Result.B := 0; end;
end;

function StudioDuration(DurationMs: cardinal): cardinal;
begin
  if Ini.ScreenFade = 0 then Result := 0 else Result := DurationMs;
end;

function StudioPageProgress(NowTick, StartTick, DurationMs: cardinal): double;
begin
  if DurationMs = 0 then Result := 1
  else Result := SmoothProgress(ElapsedTicks(NowTick, StartTick) / DurationMs);
end;

procedure StudioRoundRect(X, Y, Z, W, H, Radius: single; const Color: TRGB; Alpha: single);
const
  Segments = 6;
var
  Triangles: TTriangleList;
  Corner, Segment, N: integer;
  CX, CY, A, B: single;
begin
  if (W <= 0) or (H <= 0) or (Alpha <= 0) then Exit;
  Radius := Min(Max(Radius, 0), Min(W, H) / 2);
  if Radius < 0.1 then
  begin
    Renderer.DrawQuad(X, Y, Z, W, H, Color.R, Color.G, Color.B, Alpha);
    Exit;
  end;
  SetLength(Triangles, 4 * Segments);
  N := 0;
  for Corner := 0 to 3 do
  begin
    if (Corner = 0) or (Corner = 3) then CX := X + Radius else CX := X + W - Radius;
    if Corner < 2 then CY := Y + Radius else CY := Y + H - Radius;
    for Segment := 0 to Segments - 1 do
    begin
      A := Pi + Corner * Pi / 2 + Segment * Pi / (2 * Segments);
      B := A + Pi / (2 * Segments);
      with Triangles[N] do
      begin
        X1 := CX; Y1 := CY;
        X2 := CX + Cos(A) * Radius; Y2 := CY + Sin(A) * Radius;
        X3 := CX + Cos(B) * Radius; Y3 := CY + Sin(B) * Radius;
      end;
      Triangles[N].Z := Z;
      Triangles[N].ColR := Color.R; Triangles[N].ColG := Color.G; Triangles[N].ColB := Color.B;
      Triangles[N].Alpha := Alpha;
      Inc(N);
    end;
  end;
  Renderer.DrawTriangles(Triangles);
  Renderer.DrawQuad(X + Radius, Y, Z, W - 2 * Radius, H, Color.R, Color.G, Color.B, Alpha);
  Renderer.DrawQuad(X, Y + Radius, Z, Radius, H - 2 * Radius, Color.R, Color.G, Color.B, Alpha);
  Renderer.DrawQuad(X + W - Radius, Y + Radius, Z, Radius, H - 2 * Radius, Color.R, Color.G, Color.B, Alpha);
end;

procedure StudioButton(const Texture: TTexture; const Normal, Hover: TRGB;
  Focus, Press: single; Enabled: boolean);
var
  Fill, Border: TRGB;
  Inset, Stroke, Alpha: single;
begin
  Fill.R := Normal.R + (Hover.R - Normal.R) * Focus;
  Fill.G := Normal.G + (Hover.G - Normal.G) * Focus;
  Fill.B := Normal.B + (Hover.B - Normal.B) * Focus;
  Border := StudioColor('StudioBorder');
  if Focus > 0.1 then Border := StudioColor('StudioAccent');
  Stroke := 1 + Focus;
  Inset := Press;
  Alpha := Texture.Alpha;
  if not Enabled then Alpha := Alpha * 0.45;
  StudioRoundRect(Texture.X + Inset, Texture.Y + Inset, Texture.Z,
    Texture.W - 2 * Inset, Texture.H - 2 * Inset, Theme.Studio.Radius, Border, Alpha);
  StudioRoundRect(Texture.X + Inset + Stroke, Texture.Y + Inset + Stroke, Texture.Z,
    Texture.W - 2 * (Inset + Stroke), Texture.H - 2 * (Inset + Stroke),
    Theme.Studio.Radius - Stroke, Fill, Alpha);
end;

procedure StudioSelector(const Texture, Values: TTexture; Focus: single; Arrows: boolean);
var
  Border, Fill, Ink: TRGB;
  Stroke, MidY: single;
begin
  Border := StudioColor('StudioBorder');
  Fill := StudioColor('StudioSurface');
  Ink := StudioColor('StudioMuted');
  if Focus > 0.1 then Border := StudioColor('StudioAccent');
  Stroke := 1 + Focus;
  StudioRoundRect(Texture.X, Texture.Y, Texture.Z, Values.X + Values.W - Texture.X,
    Max(Texture.H, Values.H), Theme.Studio.Radius, Border, Texture.Alpha);
  StudioRoundRect(Texture.X + Stroke, Texture.Y + Stroke, Texture.Z,
    Values.X + Values.W - Texture.X - Stroke * 2, Max(Texture.H, Values.H) - Stroke * 2,
    Theme.Studio.Radius - Stroke, Fill, Texture.Alpha);
  StudioRoundRect(Values.X + 2, Values.Y + 3, Texture.Z, Values.W - 5, Values.H - 6,
    Theme.Studio.Radius - 2, StudioColor('StudioSoft'), Texture.Alpha);
  if Arrows then
  begin
    MidY := Values.Y + Values.H / 2;
    Renderer.DrawLine(Values.X + 14, MidY - 4, Values.X + 10, MidY, Texture.Z, 1.5, Ink.R, Ink.G, Ink.B, 1);
    Renderer.DrawLine(Values.X + 10, MidY, Values.X + 14, MidY + 4, Texture.Z, 1.5, Ink.R, Ink.G, Ink.B, 1);
    Renderer.DrawLine(Values.X + Values.W - 14, MidY - 4, Values.X + Values.W - 10, MidY, Texture.Z, 1.5, Ink.R, Ink.G, Ink.B, 1);
    Renderer.DrawLine(Values.X + Values.W - 10, MidY, Values.X + Values.W - 14, MidY + 4, Texture.Z, 1.5, Ink.R, Ink.G, Ink.B, 1);
  end;
end;

procedure LabelAt(X, Y, Size: single; const Value: UTF8String; const Color: TRGB);
begin
  SetFontFamily(0); SetFontStyle(ftRegular); SetFontSize(Size);
  SetFontItalic(false); SetFontReflection(false, 0);
  SetFontPos(X, Y); SetFontZ(0.1);
  SetFontColor(Color.R, Color.G, Color.B, 1);
  PrintText(Value);
end;

procedure StudioShell;
var
  Border: TRGB;
begin
  Border := StudioColor('StudioBorder');
  Renderer.DrawQuad(40, 50, 0, 720, 1, Border.R, Border.G, Border.B, 1);
  Renderer.DrawQuad(40, 556, 0, 720, 1, Border.R, Border.G, Border.B, 1);
  LabelAt(40, 18, 19, Language.Translate('STUDIO_BRAND'), StudioColor('StudioInk'));
  LabelAt(636, 22, 13, 'VOCAL STUDIO', StudioColor('StudioMuted'));
  LabelAt(40, 572, 16, Language.Translate('STUDIO_NAV'), StudioColor('StudioMuted'));
end;

end.
