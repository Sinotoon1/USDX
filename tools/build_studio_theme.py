"""Build the native Studio theme from semantic tokens and upstream geometry.

Legacy themes remain untouched. Reuses only functional note/cover/icon assets;
Studio buttons, panels, selectors and transitions are drawn by native code.
"""

import argparse
import configparser
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate():
    design = json.loads((ROOT / "tools/studio-design.json").read_text())
    base = configparser.RawConfigParser(strict=False)
    base.optionxform = str  # ColorExists uses the original case-sensitive names.
    base.read(ROOT / "game/themes/Modern.ini", encoding="utf-8-sig")
    sections = {}

    def put(name, **props):
        sections.setdefault(name, {}).update(
            {k.lower(): str(v) for k, v in props.items()}
        )

    def resolved(name):
        result, seen = {}, set()
        while name in base and name not in seen:
            seen.add(name)
            for key, value in base[name].items():
                result.setdefault(key.lower(), value)
            name = base[name].get("Inherits", base[name].get("inherits", ""))
        return result

    def hide(name):
        # Directly referenced theme texts are still loaded even if Enabled=0.
        put(name, Enabled=0, X=-2000, Y=-2000)

    def text(name, x, y, size, color="StudioInk", **props):
        attrs = dict(
            X=x,
            Y=y,
            Size=size,
            Font=0,
            Style=0,
            Align=0,
            Enabled=1,
            Color=color,
            DColor=color,
            Reflection=0,
            Z=0.5,
        )
        attrs.update(props)
        put(name, **attrs)

    def button(name, rect, caption, primary=False, size=24):
        x, y, w, h = rect
        put(
            name,
            X=x,
            Y=y,
            W=w,
            H=h,
            Tex="Rectangle",
            Flat=1,
            Type="Transparent",
            Color="StudioAccentHover" if primary else "StudioSoft",
            DColor="StudioAccent" if primary else "StudioSurface",
            SelectW=w,
            SelectH=h,
            Fade=0,
            FadeText=0,
            Reflection=0,
            Parent=0,
            Texts=1,
            Visible=1,
            Z=0.2,
        )
        text(
            name + "Text1",
            w // 2,
            (h - size) // 2,
            size,
            "White" if primary else "StudioInk",
            Text=caption,
        )
        put(name + "Text1", Align=1)

    # USDX falls back by SECTION, not by KEY. Materialize each inherited section
    # before applying tokens so required dimensions/Text counts never disappear.
    sections.update(
        {
            n: {k: v for k, v in resolved(n).items() if k != "inherits"}
            for n in base.sections()
        }
    )
    put(
        "Theme",
        Name="Studio",
        BaseTheme="Modern",
        Creator="USDX Coach",
        US_Version="USD 110",
        DefaultSkin="Studio",
    )
    put("Studio", Enabled=1, Radius=design["radius"], **design["motion"])
    # TTheme.LoadColors selects one entire Colors section, not key-wise merging.
    sections["Colors"] = dict(base["Colors"])
    sections["Colors"].update(
        {k: " ".join(map(str, rgb)) for k, rgb in design["colors"].items()}
    )
    for old, token in {
        "CoachSurface": "StudioStageSurface",
        "CoachSelected": "StudioSoft",
        "CoachText": "StudioStageText",
        "CoachMuted": "StudioStageMuted",
        "CoachAccent": "StudioClose",
        "CoachFlat": "StudioFlat",
        "CoachSharp": "StudioSharp",
        "CoachClose": "StudioClose",
    }.items():
        sections["Colors"][old] = sections["Colors"][token]

    source = (ROOT / "src/base/UThemes.pas").read_text()
    pages = set(re.findall(r"ThemeLoadBasic\s*\([^,]+,\s*'([^']+)'\)", source))
    pages.update(("SongRoulette", "SongChessboard", "SongList", "JukeboxSongList"))
    stage_pages = ("Sing", "Coach", "EditSub", "JukeboxSing")
    modal = (
        "CheckPopup",
        "ErrorPopup",
        "InsertUserPopup",
        "SendScorePopup",
        "ScoreDownloadPopup",
        "HelpPopup",
        "SongMenu",
        "SongJumpto",
    )
    for page in sorted(pages):
        shell = not page.startswith(stage_pages + modal)
        put(page, StudioShell=int(shell))
        if page.startswith(modal):
            put(
                page + "Background",
                Type="Fade",
                ColR=0.06,
                ColG=0.10,
                ColB=0.08,
                Alpha=0.5,
            )
        else:
            rgb = design["colors"][
                "StudioStage" if page.startswith(stage_pages) else "StudioCanvas"
            ]
            put(
                page + "Background",
                Type="Color",
                **{k: c / 255 for k, c in zip(("ColR", "ColG", "ColB"), rgb)},
            )

    for name in base.sections():
        props = resolved(name)
        stage = name.startswith(stage_pages)
        if "font" in props or ("text" in props and "size" in props):
            put(
                name,
                Font=0,
                Style=0,
                Reflection=0,
                Color="StudioStageText" if stage else "StudioInk",
                DColor="StudioStageText" if stage else "StudioInk",
            )
            if not stage and "Button" not in name and "Text" in name:
                size = int(props.get("size", 22))
                put(name, Size=min(size, 40))
            if not stage and int(props.get("y", 0)) >= 540:
                hide(name)
        if "tex" in props and "Button" in name:
            if not any(k in name for k in ("Avatar", "PlayerColor")):
                put(
                    name,
                    Tex="Rectangle",
                    Flat=1,
                    Reflection=0,
                    Fade=0,
                    FadeText=0,
                    SelectW=props.get("w", 0),
                    SelectH=props.get("h", 0),
                    FadeTex="",
                    Color="StudioSoft",
                    DColor="StudioSurface",
                )
        if "texsbg" in props or "sbgw" in props:
            put(
                name,
                Tex="Rectangle",
                TexSBG="Rectangle",
                Type="Transparent",
                TypeSBG="Transparent",
                Color="StudioSurface",
                DColor="StudioSurface",
                TColor="StudioInk",
                TDColor="StudioInk",
                SBGColor="StudioSoft",
                SBGDColor="StudioSoft",
                STColor="StudioAccent",
                STDColor="StudioMuted",
                TextSize=22,
                showArrows=1,
                oneItemOnly=1,
            )
        texture = props.get("tex", "")
        if "Static" in name and not stage:
            if texture in (
                "Leiste1",
                "Leiste2",
                "MainIcon",
                "IconOption",
            ) or texture.startswith("Button"):
                hide(name)
            elif any(
                k in texture
                for k in (
                    "Box",
                    "Glass",
                    "Selection",
                    "Frame",
                    "dialog_background",
                    "StatMainBG",
                )
            ):
                # Avatar frames and player/medley indicators retain their real assets.
                if "Avatar" not in texture:
                    put(
                        name,
                        Tex="Rectangle",
                        Flat=1,
                        Color="StudioSurface",
                        Type="Transparent",
                        Reflection=0,
                    )
        if (
            not stage
            and name.endswith("Text1")
            and "Button" not in name
            and name not in modal
        ):
            if int(props.get("size", 0)) >= 48:
                text(name, 40, 72, design["type"]["title"])

    for page in sorted(pages):
        subtitle = page + "Text2"
        props = resolved(subtitle)
        if (
            page not in modal
            and not page.startswith(stage_pages)
            and props
            and int(props.get("y", 999)) < 160
        ):
            text(subtitle, 40, 118, 20, "StudioMuted", W=720, H=32)

    # Home: two purposeful mode surfaces and direct secondary navigation.
    for i in range(1, 7):
        hide("MainStatic" + str(i))
    text("MainText1", 40, 76, 42, Text="STUDIO_HOME")
    text("MainText2", 40, 132, 22, "StudioMuted", Text="STUDIO_SUBTITLE")
    text("MainText3", 40, 378, 18, "StudioMuted", Text="STUDIO_IMPORT", W=720, H=28)
    hide("MainText4")
    text("MainTextDescription", 40, 488, 16, "StudioAccent", W=520, H=24)
    text("MainTextDescriptionLong", 40, 512, 20, "StudioMuted", W=520, H=36)
    for name, rect, title, body, action, primary in (
        (
            "MainButtonMulti",
            design["layout"]["homePractice"],
            "COACH_PRACTICE",
            "STUDIO_PRACTICE_BODY",
            "STUDIO_PRACTICE_ACTION",
            True,
        ),
        (
            "MainButtonSolo",
            design["layout"]["homePlay"],
            "COACH_PLAY",
            "STUDIO_PLAY_BODY",
            "STUDIO_PLAY_ACTION",
            False,
        ),
    ):
        button(name, rect, title)
        put(name, Texts=3)
        if primary:
            put(name, Color="StudioSoft", DColor="StudioSoft")
        ink = "StudioInk"
        text(name + "Text1", 24, 22, 32, ink, Text=title)
        text(name + "Text2", 24, 76, 21, ink, Text=body, W=rect[2] - 48, H=64)
        text(name + "Text3", 24, 144, 18, ink, Text=action)
    for i, (name, caption) in enumerate(
        (
            ("Jukebox", "SING_JUKEBOX"),
            ("Stats", "SING_STATS"),
            ("Editor", "SING_EDITOR"),
            ("Options", "SING_OPTIONS"),
        )
    ):
        button("MainButton" + name, [40 + i * 184, 416, 168, 48], caption)
    button("MainButtonAbout", [592, 510, 80, 34], "SING_ABOUT", size=18)
    button("MainButtonExit", [680, 510, 80, 34], "SING_EXIT", size=18)
    put(
        "MainButtonCollection1",
        Visible=0,
        W=0,
        H=0,
        SelectW=0,
        SelectH=0,
        Texts=0,
        FirstChild=0,
        FadeTex="",
    )

    text("NameText1", 40, 72, 36, Text="STUDIO_PROFILE")
    text("NameText2", 40, 118, 20, "StudioMuted", Text="STUDIO_PROFILE_HINT")
    put("NameSelectPlayerCount", X=40, Y=152, W=224, H=44, SkipX=8, SBGW=464)
    put("NamePlayerScrollAvatar", Count=1, Distance=0)
    put("NamePlayerAvatar", X=60, Y=324, W=112, H=112, Reflection=0)
    put(
        "NamePlayerButtonAvatar",
        X=48,
        Y=312,
        W=136,
        H=136,
        SelectW=136,
        SelectH=136,
        Flat=1,
        Tex="Rectangle",
        Color="StudioSoft",
        DColor="StudioSurface",
        Reflection=0,
        Z=0.7,
    )
    put(
        "NamePlayerButtonName",
        X=224,
        Y=312,
        W=512,
        H=48,
        SelectW=512,
        SelectH=48,
        Flat=1,
        Tex="Rectangle",
        Color="StudioSoft",
        DColor="StudioSurface",
        Z=1,
    )
    text("NamePlayerButtonNameText1", 24, 12, 24)
    put(
        "NamePlayerSelectCurrent",
        X=-4,
        Y=212,
        W=112,
        H=56,
        SelectW=112,
        SelectH=56,
        Flat=1,
        Tex="Rectangle",
        Color="StudioSoft",
        DColor="StudioSurface",
        Fade=0,
        Z=0.3,
    )
    for i in range(1, 7):
        x = 40 + (i - 1) * 120
        put(
            "NamePlayerSelectStatic" + str(i),
            X=x,
            Y=216,
            W=104,
            H=48,
            Flat=1,
            Tex="Rectangle",
            Color="StudioSurface",
            Reflection=0,
            Z=0.4,
        )
        text(
            "NamePlayerSelectStatic" + str(i) + "Text",
            x + 52,
            228,
            18,
            Align=1,
            W=100,
            H=32,
        )
        put("NamePlayerSelectStatic" + str(i) + "Avatar", W=0, H=0)
    text("NameText7", 48, 284, 20, Text="STUDIO_AVATAR")
    text("NameText8", 224, 284, 20, Text="STUDIO_NAME")
    text("NameText9", 48, 458, 16, "StudioMuted", Text="STUDIO_AVATAR_HINT")
    for name, y, caption in (
        ("NameSelectPlayerColor", 376, "STUDIO_COLOR"),
        ("NameSelectPlayerLevel", 432, "STUDIO_LEVEL"),
    ):
        put(name, X=224, Y=y, W=144, H=44, SkipX=8, SBGW=360, Text=caption, TextSize=22)
    button(
        "NameButtonContinue", [592, 504, 144, 44], "SING_LEGEND_CONTINUE", True, size=22
    )

    # Settings: larger consistent targets with room for long Chinese values.
    text("OptionsText1", 40, 72, 36, Text="STUDIO_SETTINGS")
    for i, name in enumerate(
        (
            "Game",
            "Graphics",
            "Sound",
            "Input",
            "Lyrics",
            "Themes",
            "Record",
            "Advanced",
            "Network",
            "Webcam",
            "Jukebox",
        )
    ):
        button(
            "OptionsButton" + name,
            [40 + (i % 4) * 184, 168 + (i // 4) * 96, 168, 64],
            "SING_OPTIONS_" + name.upper(),
        )
    button("OptionsButtonExit", [592, 492, 168, 44], "SING_OPTIONS_EXIT", size=22)
    text("OptionsTextDescription", 40, 444, 20, "StudioMuted", W=528, H=56)
    text("OptionsSubText1", 40, 72, 36)
    text("OptionsSubTextDescription", 40, 118, 20, "StudioMuted", W=704, H=32)
    hide("OptionsSubTextWhereAmI")
    x, y, w, h = design["layout"]["settingsArea"]
    put("OptionsSubArea", X=x, Y=y, W=w, H=h, WidgetVSpacing=10, ButtonBackVSpacing=12)
    put("OptionsSubSelectSlide", X=48, W=230, H=44, SkipX=8, SBGW=448, TextSize=22)
    put(
        "OptionsSubButton",
        X=48,
        W=686,
        H=44,
        Flat=1,
        Tex="Rectangle",
        Color="StudioSoft",
        DColor="StudioSurface",
    )
    text("OptionsSubButtonText1", 343, 10, 22)
    put("OptionsSubButtonText1", Align=1)
    put(
        "OptionsSubButtonExit",
        X=48,
        W=216,
        H=44,
        SelectW=216,
        SelectH=44,
        Flat=1,
        Color="StudioSoft",
        DColor="StudioSurface",
        FadeTex="",
    )
    put(
        "OptionsSubScrollBar",
        W=6,
        HSpacing=8,
        Color="StudioBorder",
        HColor="StudioAccent",
        CColor="StudioAccent",
    )

    for page in ("SongList", "SongRoulette", "SongChessboard"):
        for section in base.sections():
            if section.startswith((page + "TextNonParty", page + "StaticNonParty")):
                hide(section)
        text(page + "Text1", 40, 72, 36, Text="STUDIO_LIBRARY")
        text(page + "Text2", 40, 120, 18, "StudioMuted", Text="STUDIO_LIBRARY_HINT")
        text(page + "TextCat", 40, 520, 18, "StudioMuted", Text="", W=456, H=28)
        for suffix in ("Equalizer",):
            put(page + suffix, Visible=0)
    x, y, w, h, rows, pad = design["layout"]["libraryRows"]
    put(
        "SongListSelectSong",
        X=x,
        Y=y,
        W=w,
        H=h,
        Rows=rows,
        Padding=pad,
        Tex="Rectangle",
        DTex="Rectangle",
        Type="Transparent",
        Color="StudioSoft",
        DColor="StudioSurface",
        Reflection=0,
        Z=0.1,
    )
    put(
        "SongListCover",
        X=x + 8,
        Y=y + 8,
        W=48,
        H=48,
        Rows=rows,
        Padding=24,
        Reflections=0,
        SelectReflection=0,
        SelectX=528,
        SelectY=150,
        SelectW=232,
        SelectH=232,
    )
    text("SongListTextArtist", 112, 158, 18, "StudioMuted", W=340, H=22)
    text("SongListTextTitle", 112, 182, 24, W=340, H=26)
    text("SongListTextYear", 472, 187, 14, "StudioMuted", Align=2)
    text("SongListTextNumber", 540, 392, 16, "StudioMuted")
    text("SongListTextScore", 528, 404, 20)
    for name in (
        "TextMaxScore",
        "TextMediaScore",
        "TextMaxScore2",
        "TextMediaScore2",
        "TextScoreUser",
        "TextMaxScoreLocal",
        "TextMediaScoreLocal",
        "TextScoreUserLocal",
    ):
        props = resolved("SongList" + name)
        put("SongList" + name, Y=int(props.get("y", 265)) + 170)
    for icon in (
        "VideoIcon",
        "MedleyIcon",
        "CalculatedMedleyIcon",
        "DuetIcon",
        "RapIcon",
        "RapToFreestyleIcon",
    ):
        put("SongList" + icon, X=468, Y=158, W=16, H=16)

    # Stage: retained musical note/lyric geometry, entirely new chrome/controls.
    put(
        "CoachPanel",
        Tex="Rectangle",
        Flat=1,
        Color="StudioStageSurface",
        Alpha=0.98,
        Reflection=0,
    )
    for name, size in (
        ("CoachTitle", 22),
        ("CoachStatus", 36),
        ("CoachMetrics", 22),
        ("CoachState", 18),
        ("CoachHelp", 18),
    ):
        put(
            name,
            Size=size,
            Color="StudioStageText",
            DColor="StudioStageText",
            Style=0,
            Reflection=0,
        )
    for i in range(1, 7):
        put(
            "CoachButton" + str(i),
            Flat=1,
            Tex="Rectangle",
            Color="StudioSoft",
            DColor="StudioSurface",
            Z=1,
        )
        put(
            "CoachButton" + str(i) + "Text1",
            Color="StudioStageText",
            DColor="StudioStageText",
            Z=1,
        )
    for name in (
        "SingLyricsBar",
        "SingTimeBar",
        "SingSongNameStatic",
        "SingDefaultScoreBG",
    ):
        put(name, Tex="Rectangle", Flat=1, Color="StudioStageSurface", Reflection=0)
    put("SingLyricsBar", Alpha=0.88)
    put("SingTimeProgress", Color="StudioAccent")
    text("CoachPlayText", 32, 32, 36, "StudioStageText", W=728, H=56, Z=1)

    # Overview and utility pages keep the same header/content rhythm.
    for page, title in (("StatMain", "STAT_MAIN"), ("AboutMain", "ABOUT_MAIN")):
        text(page + "Text1", 40, 72, 36, Text=title)
        text(page + "Text3", 40, 118, 20, "StudioMuted")
        hide(page + "Static6")
        hide(page + "Static8")
        put(
            page + "Static7",
            X=40,
            Y=154,
            W=520,
            H=366,
            Tex="Rectangle",
            Flat=1,
            Color="StudioSurface",
            Reflection=0,
        )
        text(page + "TextOverview", 56, 170, 22, W=488, H=332)
    for i, name in enumerate(("Scores", "Singers", "Songs", "Bands", "Exit")):
        button(
            "StatMainButton" + name,
            [584, 154 + i * 72, 176, 48],
            resolved("StatMainButton" + name + "Text1").get("text", ""),
            size=22,
        )
    button("AboutMainButtonCredits", [584, 400, 176, 48], "ABOUT_USDX_CREDITS", size=22)
    button("AboutMainButtonExit", [584, 472, 176, 48], "SING_OPTIONS_EXIT", size=22)
    text("StatDetailTextDescription", 40, 118, 20, "StudioMuted")
    text("StatDetailTextPage", 540, 150, 16, "StudioMuted", Align=2)
    for i in range(1, 11):
        text("StatDetailTextList" + str(i), 56, 178 + (i - 1) * 32, 20, W=488, H=30)
    for i in (6, 8):
        hide("StatDetailStatic" + str(i))
    put(
        "StatDetailStatic7",
        X=40,
        Y=154,
        W=520,
        H=366,
        Tex="Rectangle",
        Flat=1,
        Color="StudioSurface",
        Reflection=0,
    )
    hide("EditStatic1")
    text("EditText2", 40, 118, 20, "StudioMuted")
    text("EditTextDescription", 40, 180, 24, W=704, H=96)
    button("EditButtonConvert", [40, 312, 344, 56], "SING_EDIT_BUTTON_CONVERT")
    button("EditButtonExit", [416, 312, 344, 56], "SING_EDIT_BUTTON_EXIT")
    for name in base.sections():
        texture = resolved(name).get("tex", "")
        if name.startswith("Score") and "Static" in name:
            if texture in ("ScoreEndCap", "ScoreIcon"):
                hide(name)
            elif texture.startswith(("ScoreLevel", "ScoreBar_", "ScoreLine")):
                put(
                    name,
                    Tex="Rectangle",
                    Flat=1,
                    Color="StudioBorder",
                    Type="Transparent",
                    Reflection=0,
                )

    text("ScoreText1", 40, 72, 36, Text="STUDIO_RESULT")
    text("ScoreTextArtistTitle", 40, 118, 22, "StudioMuted", W=720, H=36)
    # Modal geometry and typography do not share the main-page header/footer.
    for page in ("CheckPopup", "ErrorPopup"):
        put(
            page + "Static1",
            X=176,
            Y=154,
            W=448,
            H=272,
            Tex="Rectangle",
            Flat=1,
            Color="StudioSurface",
            Reflection=0,
            Z=0.98,
        )
        text(
            page + "Text1",
            208,
            180,
            26,
            Text="MSG_QUESTION_TITLE" if page == "CheckPopup" else "MSG_ERROR_TITLE",
        )
        put(page + "Text1", Z=1, W=384, H=40)
        text(page + "Text", 208, 234, 24, W=384, H=100)
        put(page + "Text", Z=1)
    button("CheckPopupButton1", [208, 366, 176, 40], "YES", True, size=22)
    button("CheckPopupButton2", [416, 366, 176, 40], "NO", size=22)
    button("ErrorPopupButton1", [360, 366, 232, 40], "OK", True, size=22)
    for name in ("CheckPopupButton1", "CheckPopupButton2", "ErrorPopupButton1"):
        put(name, Z=1)
        put(name + "Text1", Z=1)

    put(
        "SongMenuStatic1",
        X=176,
        Y=104,
        W=448,
        H=392,
        Flat=1,
        Tex="Rectangle",
        Color="StudioSurface",
        Z=0.98,
    )
    hide("SongMenuStatic2")
    text("SongMenuTextMenu", 208, 128, 28, Z=1)
    for i in range(1, 6):
        button(
            "SongMenuButton" + str(i), [208, 188 + (i - 1) * 56, 384, 44], "", size=22
        )
        put("SongMenuButton" + str(i), Z=1)
        text("SongMenuButton" + str(i) + "Text1", 16, 10, 22, Text="", Z=1)
        if i <= 3:
            put(
                "SongMenuSelectSlide" + str(i),
                X=208,
                Y=188 + (i - 1) * 56,
                W=0,
                H=44,
                SBGW=384,
                Z=1,
                TextSize=22,
            )

    put(
        "SongJumptoStatic1",
        X=176,
        Y=160,
        W=448,
        H=224,
        Flat=1,
        Tex="Rectangle",
        Color="StudioSurface",
        Z=0.98,
    )
    hide("SongJumptoStatic2")
    text("SongJumptoText1", 208, 184, 26, Text="STUDIO_SEARCH", Z=1)
    put("SongJumptoSelectSlideType", X=208, Y=230, W=136, H=40, SBGW=240, SkipX=8, Z=1)
    put("SongJumptoSelectSlideType", Text="STUDIO_FILTER")
    button("SongJumptoButtonSearchText", [208, 284, 384, 40], "", size=24)
    put("SongJumptoButtonSearchText", Z=1)
    text("SongJumptoButtonSearchTextText1", 16, 8, 24, Text="", W=352, H=32, Z=1)
    text(
        "SongJumptoTextFound", 208, 340, 18, "StudioMuted", Text="SONG_JUMPTO_HELP", Z=1
    )

    # No inherited bitmap fade or selection scaling may bypass flat controls.
    for name, props in sections.items():
        if "Button" in name and props.get("flat") == "1":
            put(name, SelectW=props["w"], SelectH=props["h"], FadeTex="")

    out = [
        "; Generated by tools/build_studio_theme.py; "
        "edit studio-design.json or its layout rules.\n"
    ]
    for name, props in sections.items():
        out.append("[" + name + "]\n")
        out.extend(f"{k} = {v}\n" for k, v in props.items())
        out.append("\n")
    skin = (ROOT / "game/themes/Deluxe/Blue.ini").read_text(encoding="utf-8-sig")
    skin = skin.replace("Theme=Deluxe", "Theme=Studio", 1).replace(
        "Name=Blue", "Name=Studio", 1
    )
    return {
        "game/themes/Studio.ini": "".join(out),
        "game/themes/Deluxe/Studio.ini": skin,
    }, design


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs, _ = generate()
    for relative, content in outputs.items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8-sig") != content:
                raise SystemExit("Studio generated file differs: " + relative)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
    print(
        "PASS studio_theme: semantic tokens, native skin and all generated pages match"
    )


if __name__ == "__main__":
    main()
