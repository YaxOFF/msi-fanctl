"""Hoja CSS de la aplicacion.

Una sola fuente para todo el tema. Las clases CSS las aplican los widgets
con add_css_class(). Para retocar la apariencia, editar aqui.
"""

CSS = """
* {
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    -gtk-icon-style: regular;
}

window.msifan {
    background-color: #141E26;
    color: #D9C4B8;
}

window.msifan .root-box {
    background-color: #141E26;
    color: #D9C4B8;
}

window.msifan headerbar,
window.msifan .titlebar {
    background-color: #0D0D0D;
    background-image: none;
    border-bottom: 1px solid rgba(115, 90, 81, 0.3);
    box-shadow: none;
    padding: 6px 12px;
}

window.msifan headerbar > windowhandle,
window.msifan headerbar > windowhandle > box {
    background-color: transparent;
}

window.msifan .card {
    background-color: #192330;
    border-radius: 18px;
    border: 1px solid rgba(115, 90, 81, 0.28);
}

window.msifan .card-inner { padding: 14px; }

window.msifan .lbl-section {
    color: #A6877C;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 4px;
}

window.msifan .lbl-title {
    color: #A6877C;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 3px;
}

window.msifan .lbl-big {
    color: #D9C4B8;
    font-size: 34px;
    font-weight: 800;
}

window.msifan .lbl-unit {
    color: #735A51;
    font-size: 13px;
    font-weight: 600;
}

window.msifan .lbl-sub {
    color: #A6877C;
    font-size: 11px;
    letter-spacing: 1px;
}

window.msifan .app-title {
    color: #D9C4B8;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 4px;
}

window.msifan .app-sub {
    color: #735A51;
    font-size: 8px;
    letter-spacing: 2px;
}

window.msifan .status-ok  { color: #A6877C; font-size: 9px; font-weight: 700; letter-spacing: 2px; }
window.msifan .status-err { color: #735A51; font-size: 9px; font-weight: 700; letter-spacing: 2px; }

window.msifan button.mode-btn {
    background-color: rgba(115, 90, 81, 0.12);
    background-image: none;
    color: #D9C4B8;
    border-radius: 10px;
    border: 1px solid rgba(115, 90, 81, 0.25);
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 8px 4px;
    min-width: 62px;
    box-shadow: none;
}

window.msifan button.mode-btn:hover {
    background-color: rgba(166, 135, 124, 0.20);
    background-image: none;
    border-color: rgba(166, 135, 124, 0.5);
}

window.msifan button.mode-btn.active {
    background-color: #735A51;
    background-image: none;
    border-color: #A6877C;
    color: #D9C4B8;
}

window.msifan button.profile-btn {
    background-color: rgba(115, 90, 81, 0.10);
    background-image: none;
    color: #D9C4B8;
    border-radius: 12px;
    border: 1px solid rgba(115, 90, 81, 0.20);
    font-size: 11px;
    padding: 9px 12px;
    min-width: 80px;
    box-shadow: none;
}

window.msifan button.profile-btn:hover {
    background-color: rgba(166, 135, 124, 0.18);
    background-image: none;
    border-color: rgba(166, 135, 124, 0.4);
}

window.msifan button.profile-btn.active {
    background-color: rgba(115, 90, 81, 0.42);
    background-image: none;
    border-color: #A6877C;
    color: #D9C4B8;
    font-weight: 700;
}

window.msifan button.boost-btn {
    background-color: rgba(115, 90, 81, 0.10);
    background-image: none;
    color: #A6877C;
    border-radius: 12px;
    border: 1px solid rgba(115, 90, 81, 0.22);
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 3px;
    padding: 14px 0;
    box-shadow: none;
}

window.msifan button.boost-btn:hover {
    background-color: rgba(166, 135, 124, 0.18);
    background-image: none;
}

window.msifan button.boost-btn.active {
    background-color: rgba(166, 135, 124, 0.28);
    background-image: none;
    border-color: #A6877C;
    color: #D9C4B8;
}

window.msifan separator {
    background-color: rgba(115, 90, 81, 0.18);
    min-height: 1px;
    margin: 2px 0;
}

window.msifan flowboxchild {
    background-color: transparent;
    padding: 0;
}

/* ── Editor de curvas ── */
window.editor {
    background-color: #141E26;
    color: #D9C4B8;
}
window.editor .root-box { background-color: #141E26; color: #D9C4B8; }
window.editor headerbar,
window.editor .titlebar {
    background-color: #0D0D0D;
    background-image: none;
    border-bottom: 1px solid rgba(115, 90, 81, 0.3);
    box-shadow: none;
}
window.editor .card {
    background-color: #192330;
    border-radius: 14px;
    border: 1px solid rgba(115, 90, 81, 0.28);
}
window.editor .card-inner { padding: 12px; }
window.editor .lbl-section {
    color: #A6877C;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 4px;
}
window.editor .hint { color: #735A51; font-size: 9px; letter-spacing: 1px; }
window.editor entry {
    background-color: #0D0D0D;
    background-image: none;
    color: #D9C4B8;
    border-radius: 8px;
    border: 1px solid rgba(115, 90, 81, 0.35);
    padding: 6px 10px;
    caret-color: #A6877C;
}
window.editor entry:focus { border-color: #A6877C; }
window.editor button.mode-btn {
    background-color: rgba(115, 90, 81, 0.12);
    background-image: none;
    color: #D9C4B8;
    border-radius: 10px;
    border: 1px solid rgba(115, 90, 81, 0.25);
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 8px 14px;
    box-shadow: none;
}
window.editor button.mode-btn:hover {
    background-color: rgba(166, 135, 124, 0.20);
    border-color: rgba(166, 135, 124, 0.5);
}
window.editor button.mode-btn.active {
    background-color: #735A51;
    border-color: #A6877C;
    color: #D9C4B8;
}
window.editor button.act-save {
    background-color: #735A51;
    background-image: none;
    color: #D9C4B8;
    border-radius: 10px;
    border: 1px solid #A6877C;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 10px 16px;
    box-shadow: none;
}
window.editor button.act-save:hover { background-color: #8a6c61; }
window.editor button.act-ghost {
    background-color: rgba(115, 90, 81, 0.10);
    background-image: none;
    color: #A6877C;
    border-radius: 10px;
    border: 1px solid rgba(115, 90, 81, 0.25);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 10px 16px;
    box-shadow: none;
}
window.editor button.act-ghost:hover { background-color: rgba(166, 135, 124, 0.18); }
window.editor button.act-danger { color: #C77; border-color: rgba(200, 119, 119, 0.4); }
window.editor button.act-danger:hover { background-color: rgba(200, 119, 119, 0.18); }

window.msifan button.new-btn {
    background-color: rgba(115, 90, 81, 0.10);
    background-image: none;
    color: #A6877C;
    border-radius: 10px;
    border: 1px solid rgba(115, 90, 81, 0.25);
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 6px 12px;
    box-shadow: none;
}
window.msifan button.new-btn:hover {
    background-color: rgba(166, 135, 124, 0.18);
    border-color: rgba(166, 135, 124, 0.45);
}
"""
