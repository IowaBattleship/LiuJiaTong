import logging
import queue
import threading
from enum import Enum
from logging import Logger

from core.FieldInfo import FieldInfo


class UIFramework(Enum):
    """UI framework options for the game interface."""
    TKINTER = "tkinter"
    FLET = "flet"
    KIVY = "kivy"


class GUIState(Enum):
    """Lifecycle states for GUI initialisation."""
    NOT_READY = "not_ready"        # GUI module not loaded yet
    PROXY_READY = "proxy_ready"    # Proxy registered (e.g. Flet queue), but UI not visible
    PAGE_READY = "page_ready"      # UI page created, controls exist
    FULLY_READY = "fully_ready"    # UI consuming updates, safe for direct dispatch


# Thread-safe queue for passing user-selected cards from GUI to game logic
card_queue = queue.Queue()

_gui_logger: Logger = logging.getLogger("gui")
_gui_instance = None
_gui_state = GUIState.NOT_READY
_pending_updates: list[FieldInfo] = []


def _set_gui_state(state: GUIState, instance=None) -> None:
    """Update GUI state machine and optionally replace the GUI instance."""
    global _gui_state, _gui_instance

    prev_state = _gui_state
    if state == GUIState.NOT_READY:
        _gui_instance = None
        _pending_updates.clear()
    elif instance is not None:
        _gui_instance = instance

    _gui_state = state
    _gui_logger.info(
        "GUI state transition: %s -> %s",
        prev_state.value if isinstance(prev_state, GUIState) else str(prev_state),
        state.value,
    )

    if state != GUIState.NOT_READY and _gui_instance is not None:
        _flush_pending_updates()


def _flush_pending_updates() -> None:
    """Deliver buffered updates to the active GUI instance."""
    while _pending_updates and _gui_instance is not None:
        info = _pending_updates.pop(0)
        try:
            _gui_logger.info(
                "Flushing buffered FieldInfo (client_id=%s) to GUI (state=%s)",
                info.client_id,
                _gui_state.value,
            )
            _gui_instance.update(info)
        except Exception:
            _gui_logger.exception(
                "Failed to flush buffered FieldInfo (client_id=%s)", info.client_id
            )
            break


def register_gui_proxy(instance) -> None:
    """Register a proxy GUI instance (e.g. Flet background queue)."""
    _set_gui_state(GUIState.PROXY_READY, instance)


def register_gui_page(instance) -> None:
    """Register the concrete GUI page instance."""
    _set_gui_state(GUIState.PAGE_READY, instance)


def register_gui_fully_ready(instance=None) -> None:
    """Mark the GUI as fully ready. Optional instance replacement."""
    _set_gui_state(GUIState.FULLY_READY, instance)


def update_gui(info: FieldInfo) -> None:
    """Public API: push new field info to GUI."""
    if _gui_instance is not None and _gui_state != GUIState.NOT_READY:
        _gui_logger.info(
            "update_gui: dispatch FieldInfo (client_id=%s, state=%s)",
            info.client_id,
            _gui_state.value,
        )
        _gui_instance.update(info)
    else:
        _pending_updates.append(info)
        _gui_logger.info(
            "update_gui: buffer FieldInfo (client_id=%s, state=%s, pending=%d)",
            info.client_id,
            _gui_state.value,
            len(_pending_updates),
        )


def _start_tkinter_gui(logger: Logger) -> None:
    """Start the Tkinter GUI in a daemon thread."""

    def runner():
        from gui_tkinter.gui_tkinter import run_tkinter_gui

        def on_ready(instance):
            register_gui_fully_ready(instance)

        run_tkinter_gui(logger, card_queue, on_ready)

    threading.Thread(target=runner, daemon=True).start()


def _start_flet_gui(logger: Logger, client=None) -> None:
    """Start the Flet GUI in the main thread."""
    from gui_flet.gui_flet import init_gui_flet

    init_gui_flet(logger, client)


def _start_kivy_gui(logger: Logger, client=None) -> None:
    """Start the Kivy GUI in the main thread."""
    from gui_kivy.gui_kivy import init_gui_kivy

    init_gui_kivy(logger, client)


def init_gui(logger: Logger, framework: UIFramework = UIFramework.TKINTER, client=None) -> None:
    """Entry point used by the client to bootstrap the GUI."""
    global _gui_logger

    _gui_logger = logger
    _set_gui_state(GUIState.NOT_READY)

    if framework == UIFramework.TKINTER:
        _start_tkinter_gui(logger)
    elif framework == UIFramework.FLET:
        _start_flet_gui(logger, client)
    elif framework == UIFramework.KIVY:
        _start_kivy_gui(logger, client)
    else:
        raise ValueError(f"Unknown UI framework: {framework}")