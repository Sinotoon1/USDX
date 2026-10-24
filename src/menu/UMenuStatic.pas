{* UltraStar Deluxe - Karaoke Game
 *
 * UltraStar Deluxe is the legal property of its developers, whose names
 * are too numerous to list here. Please refer to the COPYRIGHT
 * file distributed with this source distribution.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; see the file COPYING. If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA 02110-1301, USA.
 *
 * $URL: svn://basisbit@svn.code.sf.net/p/ultrastardx/svn/trunk/src/menu/UMenuStatic.pas $
 * $Id: UMenuStatic.pas 1692 2009-04-24 18:43:12Z k-m_schindler $
 *}

unit UMenuStatic;

interface

{$IFDEF FPC}
  {$MODE Delphi}
{$ENDIF}

{$I switches.inc}

uses
  UIMotion,
  URenderer,
  UMenuInteract;

type
  TStatic = class
    public
      Texture:           TTexture; // Button Screen position and size
      Visible:           boolean;
      Flat:              boolean;
      Hovered, Selected: boolean;
      HoverMotion: TUIMotion;

      // for list item
      TextureSelect:     TTexture;
      TextureDeselect:   TTexture; // Button Screen position and size

      //Reflection Mod
      Reflection:        boolean;
      Reflectionspacing: single;

      procedure Draw;
      constructor Create(Textura: TTexture); overload;
      destructor Destroy; override;
      function GetMouseOverArea: TMouseOverRect;
  end;

implementation
uses
  UDisplay, UCommon, UStudioUI, UThemes, sdl2;

procedure TStatic.Draw;
var
  Fill, Hover: TRGB;
  Progress: single;
begin
  if Visible then
  begin
    if Flat then
    begin
      Fill.R := Texture.ColR * Texture.Int; Fill.G := Texture.ColG * Texture.Int; Fill.B := Texture.ColB * Texture.Int;
      RetargetMotion(HoverMotion, Ord(Hovered), SDL_GetTicks, StudioDuration(Theme.Studio.HoverMs));
      Progress := MotionValue(HoverMotion, SDL_GetTicks);
      Hover := StudioColor('StudioSoft');
      Fill.R := Fill.R + (Hover.R - Fill.R) * Progress;
      Fill.G := Fill.G + (Hover.G - Fill.G) * Progress;
      Fill.B := Fill.B + (Hover.B - Fill.B) * Progress;
      StudioRoundRect(Texture.X, Texture.Y, Texture.Z, Texture.W, Texture.H, Theme.Studio.Radius, Fill, Texture.Alpha);
      if Selected then
        StudioRoundRect(Texture.X + 2, Texture.Y + 10, Texture.Z, 3, Texture.H - 20, 1,
          StudioColor('StudioAccent'), Texture.Alpha);
      Exit;
    end;
    Texture.Reflection := Reflection;
    Texture.ReflectionSpacing := ReflectionSpacing;
    Renderer.DrawTexture(Texture);
  end;
end;

constructor TStatic.Create(Textura: TTexture);
begin
  inherited Create;
  Texture := Textura;
end;

destructor TStatic.Destroy();
begin
  Texture.Free;
  TextureSelect.Free;
  TextureDeselect.Free;
  inherited;
end;

function TStatic.GetMouseOverArea: TMouseOverRect;
begin
  if not(Display.Cursor_HiddenByScreen) then
  begin
    Result.X := Texture.X;
    Result.Y := Texture.Y;
    Result.W := Texture.W;
    Result.H := Texture.H;
  end;
end;

end.
