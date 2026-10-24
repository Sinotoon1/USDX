"""Desktop cursor contract, supplemented by isolated native pointer-position QA."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DesktopPointerTests(unittest.TestCase):
    def test_studio_uses_visible_system_cursor_without_software_double_draw(self):
        source = (ROOT/'src/menu/UDisplay.pas').read_text(encoding='utf-8')
        setter = source.split('procedure TDisplay.SetCursor(', 1)[1].split('procedure TDisplay.UpdateCursorFade', 1)[0]
        self.assertIn('if Theme.Studio.Enabled then', setter)
        self.assertIn('SDL_ShowCursor(SDL_ENABLE)', setter)
        draw = source.split('procedure TDisplay.DrawCursor;', 1)[1]
        self.assertIn('if Theme.Studio.Enabled then Exit', draw)

    def test_leave_and_focus_loss_release_capture_and_cancel_pressed_target(self):
        source = (ROOT/'src/base/UMain.pas').read_text(encoding='utf-8')
        self.assertIn('SDL_WINDOWEVENT_FOCUS_LOST, SDL_WINDOWEVENT_LEAVE', source)
        self.assertIn('Display.ReleasePointer', source)
        display = (ROOT/'src/menu/UDisplay.pas').read_text(encoding='utf-8')
        release = display.split('procedure TDisplay.ReleasePointer;', 1)[1].split('procedure TDisplay.SetCursor', 1)[0]
        for token in ('CancelPointerInput', 'SDL_CaptureMouse(SDL_FALSE)',
                      'SDL_SetRelativeMouseMode(SDL_FALSE)', 'SDL_SetWindowGrab(Screen, SDL_FALSE)'):
            self.assertIn(token, release)
        self.assertNotIn('SDL_WarpMouse', release)
        self.assertIn("'SDL_MOUSE_AUTO_CAPTURE', '0'", display)


if __name__ == '__main__':
    unittest.main()
