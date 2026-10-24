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
 * $URL: svn://basisbit@svn.code.sf.net/p/ultrastardx/svn/trunk/src/screens/UScreenMain.pas $
 * $Id: UScreenMain.pas 3128 2015-08-28 01:45:23Z basisbit $
 *}

unit UScreenMain;

interface

{$IFDEF FPC}
  {$MODE Delphi}
{$ENDIF}

{$I switches.inc}

uses
  UConfig,
  UCoachCore,
  UDisplay,
  UFiles,
  UMenu,
  UMusic,
  UScreenSong,
  USong,
  UThemes,
  MD5,
  sdl2,
  SysUtils;

type

  TScreenMain = class(TMenu)
  public
    TextDescription:     integer;
    TextDescriptionLong: integer;
    procedure StartCoach(Mode: TCoachMode);

    constructor Create; override;
    function ParseInput(PressedKey: Cardinal; CharCode: UCS4Char;
      PressedDown: boolean): boolean; override;
    function ParseMouse(MouseButton: integer; BtnDown: boolean; X, Y: integer): boolean; override;
    procedure OnShow; override;
    procedure SetInteraction(Num: integer); override;
    function Draw: boolean; override;
  end;

const
  ID = 'ID_001';   //for help system

var
  WantSoftwareRenderingMsg: boolean;

implementation

uses
  UGraphic,
  UHelp,
  UIni,
  ULanguage,
  ULog,
  UNote,
  UParty,
  URenderer,
  USkins,
  USongs,
  UUnicodeUtils;

function TScreenMain.ParseInput(PressedKey: Cardinal; CharCode: UCS4Char;
  PressedDown: boolean): boolean;
begin
  Result := true;

  if (PressedDown) then
  begin // Key Down
        // check normal keys
    case PressedKey of
      SDLK_F6: begin StartCoach(cmPractice); Exit; end;
      SDLK_F5: begin StartCoach(cmPlay); Exit; end;
      SDLK_F7: begin
        if Theme.Studio.Enabled then FadeTo(@ScreenCoachImport, SoundLib.Start);
        Exit;
      end;
      SDLK_S: begin
        StartCoach(cmPlay);
        Exit;
      end;

      SDLK_P: begin
        if (Ini.Players >= 1) and (Party.ModesAvailable) then
        begin
          FadeTo(@ScreenPartyOptions, SoundLib.Start);
          Exit;
        end;
      end;

      SDLK_J: begin
        FadeTo(@ScreenJukeboxPlaylist, SoundLib.Start);
        Exit;
      end;

      SDLK_R: begin
        UGraphic.UnLoadScreens();
        Theme.LoadTheme(Ini.Theme, Ini.Color);
        UGraphic.LoadScreens(USDXVersionStr);
      end;

      SDLK_T: begin
        FadeTo(@ScreenStatMain, SoundLib.Start);
        Exit;
      end;

      SDLK_E: begin
        FadeTo(@ScreenEdit, SoundLib.Start);
        Exit;
      end;

      SDLK_O: begin
        FadeTo(@ScreenOptions, SoundLib.Start);
        Exit;
      end;

      SDLK_A: begin
        FadeTo(@ScreenAbout, SoundLib.Start);
        Exit;
      end;

      SDLK_C: begin
        ScreenAbout.ShowCreditsInAbout;
        FadeTo(@ScreenAbout, SoundLib.Start);
        Exit;
      end;

      SDLK_Q: begin
        Result := false;
        Exit;
      end;
    end;

    // check special keys
    case PressedKey of
      SDLK_ESCAPE,
      SDLK_BACKSPACE:
      begin
        Result := false;
      end;

      SDLK_TAB:
      begin
        ScreenPopupHelp.ShowPopup();
      end;

      SDLK_RETURN:
      begin
        // reset
        Party.bPartyGame := false;

        // The two modes share the same song catalogue and audio engine.
        if Interaction = 0 then StartCoach(cmPlay);

        // First-class practice entry; Party remains on the P shortcut.
        if Interaction = 1 then StartCoach(cmPractice);

        //Jukebox
        if Interaction = 2 then
        begin
          if (Songs.SongList.Count >= 1) then
          begin
            FadeTo(@ScreenJukeboxPlaylist, SoundLib.Start);
          end
          else //show error message, No Songs Loaded
            ScreenPopupError.ShowPopup(Language.Translate('ERROR_NO_SONGS'));
        end;

        //Stats
        if Interaction = 3 then
        begin
          FadeTo(@ScreenStatMain, SoundLib.Start);
        end;

        //Editor
        if Interaction = 4 then
        begin
          {$IFDEF UseMIDIPort}
          FadeTo(@ScreenEdit, SoundLib.Start);
          {$ELSE}
          ScreenPopupError.ShowPopup(Language.Translate('ERROR_NO_EDITOR'));
          {$ENDIF}
        end;

        //Options
        if Interaction = 5 then
        begin
          FadeTo(@ScreenOptions, SoundLib.Start);
        end;

        //About
        if Interaction = 6 then
        begin
          FadeTo(@ScreenAbout, SoundLib.Start);
        end;

        //Exit
        if Interaction = 7 then
        begin
          Result := false;
        end;
        if (Interaction = 8) and Theme.Studio.Enabled then
          FadeTo(@ScreenCoachImport, SoundLib.Start);
      end;
      {**
       * Up and Down could be done at the same time,
       * but I don't want to declare variables inside
       * functions like this one, called so many times
       *}
      SDLK_DOWN: InteractInc;
      SDLK_UP: InteractDec;
      SDLK_RIGHT: InteractNext;
      SDLK_LEFT: InteractPrev;
    end;
  end
  else // Key Up
    case PressedKey of
      SDLK_RETURN:
      begin
      end;
    end;
end;

function TScreenMain.ParseMouse(MouseButton: integer; BtnDown: boolean; X, Y: integer): boolean;
begin
  // default mouse behaviour
  Result := inherited ParseMouse(MouseButton, BtnDown, X, Y);
end;

constructor TScreenMain.Create;
begin
  inherited Create;
{**
 * Attention ^^:
 * New Creation Order needed because of LoadFromTheme
 * and Button Collections.
 * At First Custom Texts and Statics
 * Then LoadFromTheme
 * after LoadFromTheme the Buttons and Selects
 *}
  TextDescription     := AddText(Theme.Main.TextDescription);
  TextDescriptionLong := AddText(Theme.Main.TextDescriptionLong);

  LoadFromTheme(Theme.Main);

  AddButton(Theme.Main.ButtonSolo);
  AddButton(Theme.Main.ButtonMulti);
  AddButton(Theme.Main.ButtonJukebox);
  AddButton(Theme.Main.ButtonStat);
  AddButton(Theme.Main.ButtonEditor);
  AddButton(Theme.Main.ButtonOptions);
  AddButton(Theme.Main.ButtonAbout);
  AddButton(Theme.Main.ButtonExit);
  if Theme.Studio.Enabled then AddButton(Theme.Main.ButtonImport);

  if Length(Button[0].Text) > 0 then Button[0].Text[0].Text := Language.Translate('COACH_PLAY');
  if Length(Button[1].Text) > 0 then Button[1].Text[0].Text := Language.Translate('COACH_PRACTICE');
  Interaction := 1;

  WantSoftwareRenderingMsg := Renderer.SoftwareRendering;
end;

procedure TScreenMain.StartCoach(Mode: TCoachMode);
begin
  if Songs.SongList.Count < 1 then
  begin
    if Theme.Studio.Enabled then ScreenPopupError.ShowPopup(Language.Translate('STUDIO_NO_SONGS'))
    else ScreenPopupError.ShowPopup(Language.Translate('COACH_NO_SONGS'));
    Exit;
  end;
  CoachMode := Mode;
  if Mode = cmPractice then Log.LogStatus('Practice selected', 'CoachMode')
  else Log.LogStatus('Play selected', 'CoachMode');
  CoachDelayConfirmed := false;
  Party.bPartyGame := false;
  ScreenSong.Mode := smNormal;
  if Mode = cmPractice then PlayersPlay := 1
  else if Ini.Players = 4 then PlayersPlay := 6
  else PlayersPlay := Ini.Players+1;
  if Ini.OnSongClick = sSelectPlayer then FadeTo(@ScreenSong)
  else
  begin
    ScreenName.Goto_SingScreen := false;
    FadeTo(@ScreenName, SoundLib.Start);
  end;
end;

procedure TScreenMain.OnShow;
begin
  inherited;

  SoundLib.StartBgMusic;

  ScreenSong.Mode := smNormal;
  CoachMode := cmPlay;
  CoachDelayConfirmed := false;

  if not Help.SetHelpID(ID) then
    Log.LogWarn('No Entry for Help-ID ' + ID, 'ScreenMains');

 {**
  * Clean up TPartyGame here
  * at the moment there is no better place for this
  *}
  Party.Clear;
end;

function TScreenMain.Draw: boolean;
begin
  Result := inherited Draw;

  if not ScreenPopupError.Visible then
  begin
    if WantSoftwareRenderingMsg then
    begin
      WantSoftwareRenderingMsg := false;
      ScreenPopupError.ShowPopup(Language.Translate('ERROR_SOFTWARE_RENDERING'));
    end;
  end;
end;

procedure TScreenMain.SetInteraction(Num: integer);
begin
  inherited SetInteraction(Num);
  if Num = 8 then
  begin
    Text[TextDescription].Text := Language.Translate('IMPORT_TITLE');
    Text[TextDescriptionLong].Text := Language.Translate('IMPORT_HINT');
    Exit;
  end;
  Text[TextDescription].Text     := Theme.Main.Description[Interaction];
  Text[TextDescriptionLong].Text := Theme.Main.DescriptionLong[Interaction];
  if Interaction = 0 then
  begin
    Text[TextDescription].Text := Language.Translate('COACH_PLAY');
    Text[TextDescriptionLong].Text := Language.Translate('COACH_PLAY_HELP');
  end;
  if Interaction = 1 then
  begin
    Text[TextDescription].Text := Language.Translate('COACH_PRACTICE');
    Text[TextDescriptionLong].Text := Language.Translate('COACH_PRACTICE_HELP');
  end;
end;

end.
