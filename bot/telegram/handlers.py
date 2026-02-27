import os
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

from bot.config import ADMIN_IDS
from bot.core.controller import SystemController
from bot.monitor.server import ServerMonitor
from bot.storage.status_store import StatusStore
from bot.telegram.formatter_optimized import (
    format_daily_report, format_ping, format_ports,
    format_services, format_status,
)
from bot.telegram.keyboards import (
    back_home, clear_logs_keyboard, confirm_keyboard,
    main_menu_keyboard, security_keyboard, services_keyboard,
    settings_keyboard, ssh_keyboard,
)

BOT_SVC = "tg-control-agent"

def _admin(uid): return not ADMIN_IDS or uid in ADMIN_IDS
def _g(ctx, k):  return ctx.bot_data[k]

async def _no_access(update):
    m = update.message or (update.callback_query.message if update.callback_query else None)
    if m: await m.reply_text("No access.")

async def _home(update, context):
    mon  = _g(context, "monitor")
    sto  = _g(context, "store")
    text = format_status(mon, sto.get_settings())
    kb   = main_menu_keyboard()
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
            return
        except Exception:
            pass
    await context.bot.send_message(update.effective_chat.id, text, parse_mode="Markdown", reply_markup=kb)


# ── Commands ──────────────────────────────────────────────────────────────────

async def cmd_start(u, c):  await _home(u, c)
async def cmd_status(u, c): await _home(u, c)
async def cmd_menu(u, c):   await _home(u, c)


async def cmd_ping(update, context):
    if not context.args:
        await update.message.reply_text("Usage: `/ping <host>`", parse_mode="Markdown"); return
    host = context.args[0]
    await update.message.reply_text(f"Pinging `{host}`...", parse_mode="Markdown")
    await update.message.reply_text(
        format_ping(_g(context, "monitor").ping_host(host)),
        parse_mode="Markdown", reply_markup=back_home())


async def cmd_services(update, context):
    sto = _g(context, "store")
    s   = sto.get_settings()
    await update.message.reply_text(
        format_services(_g(context, "monitor").get_running_services(), s),
        parse_mode="Markdown", reply_markup=services_keyboard(s["services_mode"]))


async def cmd_ports(update, context):
    await update.message.reply_text(
        format_ports(_g(context, "monitor").get_open_ports()),
        parse_mode="Markdown", reply_markup=back_home())


async def _confirm(update, cb, msg, danger=False):
    await update.message.reply_text(
        msg, reply_markup=confirm_keyboard(cb, danger), parse_mode="Markdown")


async def cmd_restart_service(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args:
        await update.message.reply_text("Usage: `/restart_service <name>`", parse_mode="Markdown"); return
    name = context.args[0]
    warn = "\n\n*WARNING: this is the bot service!*" if name == BOT_SVC else ""
    await _confirm(update, f"restart_service:{name}", f"Restart `{name}`?{warn}", danger=bool(warn))


async def cmd_stop_service(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args:
        await update.message.reply_text("Usage: `/stop_service <name>`", parse_mode="Markdown"); return
    name = context.args[0]
    warn = "\n\n*WARNING: bot will stop responding!*" if name == BOT_SVC else ""
    await _confirm(update, f"stop_service:{name}", f"Stop `{name}`?{warn}", danger=bool(warn))


async def cmd_reboot(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    await _confirm(update, "reboot_server", "↻ Reboot server?", danger=True)


async def cmd_logs(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args:
        await update.message.reply_text("Usage: `/logs <service> [lines]`", parse_mode="Markdown"); return
    svc   = context.args[0]
    lines = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 50
    logs  = _g(context, "monitor").get_logs(svc, lines)
    if len(logs) > 3800: logs = logs[-3800:]
    await update.message.reply_text(
        f"*Logs {svc}:*\n```\n{logs}\n```",
        parse_mode="Markdown", reply_markup=back_home())


async def cmd_close_port(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: `/close_port <port>`", parse_mode="Markdown"); return
    await _confirm(update, f"close_port:{context.args[0]}",
                   f"Close port `{context.args[0]}`?", danger=True)


async def cmd_link_channel(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args:
        await update.message.reply_text(
            "Usage: `/link_channel <id>`\n\n"
            "Get channel ID: forward any post from the channel to @userinfobot",
            parse_mode="Markdown"); return
    try:
        cid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ID. Example: `-1001234567890`", parse_mode="Markdown"); return
    sto = _g(context, "store")
    try:
        sent = await context.bot.send_message(
            cid, format_status(_g(context, "monitor"), sto.get_settings()), parse_mode="Markdown")
        sto.add_channel(cid, sent.message_id)
        await update.message.reply_text(f"Channel `{cid}` linked!", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(
            f"Failed: `{e}`\nMake sure bot is admin with post permission.", parse_mode="Markdown")


async def cmd_broadcast(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast <text>`", parse_mode="Markdown"); return
    text     = " ".join(context.args)
    channels = _g(context, "store").get_channels()
    if not channels: await update.message.reply_text("No linked channels"); return
    ok = 0
    for cid in channels:
        try: await context.bot.send_message(cid, f"[broadcast] {text}"); ok += 1
        except Exception as e: print(f"broadcast {cid}: {e}")
    await update.message.reply_text(f"Sent to {ok} chat(s)")


async def cmd_report(update, context):
    await update.message.reply_text(
        format_daily_report(_g(context, "store").get_daily_stats()),
        parse_mode="Markdown", reply_markup=back_home())


async def cmd_set_report_time(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args:
        await update.message.reply_text("Usage: `/set_report_time 09:00`", parse_mode="Markdown"); return
    _g(context, "store").update_settings(daily_report_time=context.args[0])
    await update.message.reply_text(f"Report time: `{context.args[0]}`", parse_mode="Markdown")


async def cmd_set_reboot_time(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args:
        await update.message.reply_text("Usage: `/set_reboot_time 04:00`", parse_mode="Markdown"); return
    _g(context, "store").update_settings(auto_reboot_time=context.args[0])
    await update.message.reply_text(f"Auto-reboot: `{context.args[0]}`", parse_mode="Markdown")


async def cmd_set_alerts(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: `/set_alerts <cpu> <ram> <disk>`\nExample: `/set_alerts 80 85 90`",
            parse_mode="Markdown"); return
    cpu, ram, disk = int(context.args[0]), int(context.args[1]), int(context.args[2])
    _g(context, "store").update_settings(alert_cpu=cpu, alert_ram=ram, alert_disk=disk)
    await update.message.reply_text(
        f"Thresholds: CPU>{cpu}% RAM>{ram}% Disk>{disk}%", parse_mode="Markdown")


async def cmd_add_ssh_key(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not context.args:
        await update.message.reply_text(
            "*⚿ Add SSH key*\n\n"
            "Usage: `/add_ssh_key <pubkey>`\n"
            "Specific user: `/add_ssh_key <pubkey> --user tarpy`\n\n"
            "Generate key:\n```\nssh-keygen -t ed25519\ncat ~/.ssh/id_ed25519.pub\n```",
            parse_mode="Markdown"); return
    args     = list(context.args)
    username = "root"
    if "--user" in args:
        i = args.index("--user")
        if i + 1 < len(args):
            username = args[i + 1]
            args = [a for j, a in enumerate(args) if j != i and j != i + 1]
    pubkey = " ".join(args)
    if not (pubkey.startswith("ssh-") or pubkey.startswith("ecdsa-")):
        await update.message.reply_text(
            "Invalid key format (must start with ssh- or ecdsa-)", parse_mode="Markdown"); return
    ok, msg = _g(context, "controller").add_ssh_key(pubkey, username)
    await update.message.reply_text(f"{'✓' if ok else '✕'} {msg}", reply_markup=back_home())


async def cmd_upload_file(update, context):
    if not _admin(update.effective_user.id): await _no_access(update); return
    if not update.message.document:
        await update.message.reply_text(
            "*Upload file*\n\nSend any file as document.\nSaved to `/tmp/tg_uploads/`",
            parse_mode="Markdown"); return
    doc  = update.message.document
    dest = "/tmp/tg_uploads/" + doc.file_name
    os.makedirs("/tmp/tg_uploads", exist_ok=True)
    await update.message.reply_text(f"Downloading `{doc.file_name}`...", parse_mode="Markdown")
    try:
        f = await context.bot.get_file(doc.file_id)
        await f.download_to_drive(dest)
        await update.message.reply_text(
            f"✓ Saved: `{dest}`\nSize: {doc.file_size // 1024} KB",
            parse_mode="Markdown", reply_markup=back_home())
    except Exception as e:
        await update.message.reply_text(f"✕ Error: `{e}`", parse_mode="Markdown")


# ── Callbacks ─────────────────────────────────────────────────────────────────

TIPS = {
    "cmd:ping_prompt":       "Type: `/ping google.com`",
    "cmd:logs_prompt":       "Type: `/logs nginx 50`",
    "cmd:restart_prompt":    "Type: `/restart_service nginx`",
    "cmd:stop_prompt":       "Type: `/stop_service nginx`",
    "cmd:close_port_prompt": "Type: `/close_port 8080`",
}

TOGGLES = {
    "settings:toggle_services": "show_services",
    "settings:toggle_ports":    "show_ports",
    "settings:toggle_alerts":   "alerts_enabled",
    "settings:toggle_report":   "daily_report_enabled",
    "settings:toggle_reboot":   "auto_reboot_enabled",
}


async def handle_callbacks(update, context):
    q   = update.callback_query
    await q.answer()
    d   = q.data
    ctl = _g(context, "controller")
    mon = _g(context, "monitor")
    sto = _g(context, "store")

    async def edit(text, kb_=None, md=True):
        try:
            await q.edit_message_text(
                text, parse_mode="Markdown" if md else None, reply_markup=kb_)
        except Exception:
            pass

    if d == "cancel":               await edit("Cancelled", md=False); return
    if d == "cmd:home":             await _home(update, context);       return
    if d == "cmd:refresh":          await edit(format_status(mon, sto.get_settings()), main_menu_keyboard()); return
    if d in TIPS:                   await edit(TIPS[d], back_home());   return

    if d == "cmd:services":
        s = sto.get_settings()
        await edit(format_services(mon.get_running_services(), s), services_keyboard(s["services_mode"])); return

    if d == "cmd:autostart":
        svcs = ctl.get_autostart_services()
        text = "*⚙ Autostart*\n\n" + "\n".join(f"  + `{s}`" for s in svcs) if svcs else "None"
        await edit(text, back_home()); return

    if d.startswith("svcmode:"):
        mode = d.split(":", 1)[1]
        sto.update_settings(services_mode=mode)
        s = sto.get_settings()
        await edit(format_services(mon.get_running_services(), s), services_keyboard(mode)); return

    if d == "cmd:ports":
        await edit(format_ports(mon.get_open_ports()), back_home()); return

    if d == "cmd:reboot":
        await edit("↻ Reboot server?", confirm_keyboard("reboot_server", danger=True)); return

    if d == "cmd:settings":
        s  = sto.get_settings()
        ch = sto.get_channels()
        ids = "\n".join(f"  `{c}`" for c in ch) if ch else ""
        await edit(f"*≡ Settings*\n\nLinked: {len(ch)}\n{ids}", settings_keyboard(s)); return

    if d == "cmd:ssh_menu":
        import subprocess
        active = subprocess.run(
            ["systemctl", "is-active", "ssh"],
            capture_output=True, text=True).stdout.strip() == "active"
        await edit(f"*⚿ SSH*\n\nStatus: {'active' if active else 'stopped'}", ssh_keyboard(active)); return

    if d == "cmd:security":
        await edit("*⛨ Security*", security_keyboard()); return

    if d == "ssh:start":
        ok, msg = ctl.ssh_enable()
        await edit(f"{'✓' if ok else '✕'} {msg}", back_home()); return

    if d == "ssh:stop":
        await edit(
            "Stop SSH?\n\nSSH access will be cut. Bot stays accessible.",
            confirm_keyboard("ssh:stop_confirm", danger=True)); return

    if d == "ssh:stop_confirm":
        ok, msg = ctl.ssh_disable()
        await edit(f"{'✓' if ok else '✕'} {msg}", back_home()); return

    if d == "ssh:add_key":
        await edit(
            "Send:\n`/add_ssh_key <pubkey>`\n\nFor specific user:\n`/add_ssh_key <pubkey> --user tarpy`",
            back_home()); return

    if d == "ssh:keygen_info":
        await edit(
            "*⚿ SSH Key Guide*\n\n"
            "1. Generate key:\n```\nssh-keygen -t ed25519\n```\n"
            "2. Show public key:\n```\ncat ~/.ssh/id_ed25519.pub\n```\n"
            "3. Add via bot:\n`/add_ssh_key <paste key here>`",
            back_home()); return

    if d in TOGGLES:
        key = TOGGLES[d]
        s   = sto.get_settings()
        sto.update_settings(**{key: not s[key]})
        await edit("*≡ Settings*", settings_keyboard(sto.get_settings())); return

    if d == "settings:send_status":
        channels = sto.get_channels()
        if not channels:
            await edit("No linked channels. Use 'Link this chat' or `/link_channel <ID>`",
                       settings_keyboard(sto.get_settings())); return
        text    = format_status(mon, sto.get_settings())
        ok_n    = 0
        errors  = []
        for cid in list(channels):
            try:
                sent = await context.bot.send_message(cid, text, parse_mode="Markdown")
                sto.add_channel(cid, sent.message_id)
                ok_n += 1
            except Exception as e:
                errors.append(f"`{cid}`: {e}")
        result = f"✓ Sent to {ok_n} chat(s)"
        if errors: result += "\n\nErrors:\n" + "\n".join(errors)
        await edit(result, settings_keyboard(sto.get_settings())); return

    if d == "settings:add_channel":
        text = format_status(mon, sto.get_settings())
        sent = await context.bot.send_message(q.message.chat_id, text, parse_mode="Markdown")
        sto.add_channel(q.message.chat_id, sent.message_id)
        await edit(f"✓ Chat `{q.message.chat_id}` linked!", settings_keyboard(sto.get_settings())); return

    if d == "settings:add_by_id":
        await edit(
            "*⊕ Link channel by ID*\n\n"
            "1. Add bot as admin with post permission\n"
            "2. Get channel ID via @userinfobot\n"
            "3. Send: `/link_channel -1001234567890`",
            back_home()); return

    if d == "settings:remove_channel":
        sto.remove_channel(q.message.chat_id)
        await edit("Unlinked.", settings_keyboard(sto.get_settings())); return

    if d == "settings:blacklist_info":
        bl = ", ".join(sto.get_settings()["services_blacklist"]) or "empty"
        await edit(f"*Hidden services:*\n`{bl}`\n\nChange: `/set_blacklist s1,s2`", back_home()); return

    if d.startswith("restart_service:"):
        name = d.split(":", 1)[1]
        await edit(f"Restarting `{name}`...")
        ok, msg = ctl.service_action("restart", name)
        await edit(f"{'✓' if ok else '✕'} {msg}", back_home()); return

    if d.startswith("stop_service:"):
        name = d.split(":", 1)[1]
        await edit(f"Stopping `{name}`...")
        ok, msg = ctl.service_action("stop", name)
        await edit(f"{'✓' if ok else '✕'} {msg}", back_home()); return

    if d == "reboot_server":
        ok, _ = ctl.reboot_server()
        if ok:
            for cid in sto.get_channels():
                try: await context.bot.send_message(cid, "↻ Server rebooting. Back in ~1 min.")
                except Exception: pass
            await edit("Rebooting in 5 sec...")
        else:
            await edit("✕ Reboot failed")
        return

    if d == "clear_journalctl":
        await edit("Clearing logs...")
        ok, msg = ctl.clear_journal()
        await edit(f"{'✓' if ok else '✕'} {msg}", back_home()); return

    if d.startswith("close_port:"):
        port = int(d.split(":", 1)[1])
        await edit(f"Closing port {port}...")
        ok, msg = ctl.close_port(port)
        await edit(f"{'✓' if ok else '✕'} {msg}", back_home()); return


# ── Auto-join ─────────────────────────────────────────────────────────────────

async def handle_new_member(update, context):
    for m in update.message.new_chat_members:
        if m.id == context.bot.id:
            sto  = _g(context, "store")
            text = format_status(_g(context, "monitor"), sto.get_settings())
            sent = await context.bot.send_message(
                update.effective_chat.id, text, parse_mode="Markdown")
            sto.add_channel(update.effective_chat.id, sent.message_id)
            print(f"Auto-added to {update.effective_chat.id}")


async def handle_document(update, context):
    if _admin(update.effective_user.id):
        await cmd_upload_file(update, context)


# ── Background jobs ───────────────────────────────────────────────────────────

async def _push_status(context):
    mon = _g(context, "monitor")
    sto = _g(context, "store")
    s   = sto.get_settings()
    # collect metrics once
    cpu = max(0.0, mon.get_cpu_usage())
    mem = mon.get_memory_usage()
    dsk = mon.get_disk_usage()
    net = mon.get_network_stats()
    sto.record_stats(cpu, mem["percent"], dsk["percent"], net["recv"], net["sent"])
    text = format_status(mon, s)
    for cid, mid in list(sto.get_channels().items()):
        try:
            await context.bot.edit_message_text(
                chat_id=cid, message_id=mid, text=text, parse_mode="Markdown")
        except Exception as e:
            if any(x in str(e).lower() for x in [
                "message to edit not found", "can't be edited",
                "chat not found", "bot was blocked",
            ]):
                try:
                    sent = await context.bot.send_message(cid, text, parse_mode="Markdown")
                    sto.add_channel(cid, sent.message_id)
                    print(f"Re-sent to {cid}")
                except Exception as e2:
                    print(f"{cid}: {e2}")
            else:
                print(f"{cid}: {e}")


async def job_update_status(context): await _push_status(context)

_alerted: set = set()


async def job_alerts(context):
    sto = _g(context, "store")
    s   = sto.get_settings()
    if not s["alerts_enabled"]: return
    mon = _g(context, "monitor")
    cpu = max(0.0, mon.get_cpu_usage())
    mem = mon.get_memory_usage()
    dsk = mon.get_disk_usage()
    hits = []
    if cpu            > s["alert_cpu"]:  hits.append(f"CPU `{cpu:.1f}%` > {s['alert_cpu']}%")
    if mem["percent"] > s["alert_ram"]:  hits.append(f"RAM `{mem['percent']:.1f}%` > {s['alert_ram']}%")
    if dsk["percent"] > s["alert_disk"]: hits.append(f"Disk `{dsk['percent']:.1f}%` > {s['alert_disk']}%")
    key = str(sorted(hits))
    if not hits: _alerted.discard(key); return
    if key in _alerted: return
    _alerted.add(key)
    text = "*⚠ ALERT — High load*\n\n" + "\n".join(hits)
    for cid in sto.get_channels():
        try: await context.bot.send_message(cid, text, parse_mode="Markdown")
        except Exception as e: print(f"alert {cid}: {e}")


_report_at = _reboot_at = None


async def job_daily_report(context):
    global _report_at
    sto = _g(context, "store")
    s   = sto.get_settings()
    if not s["daily_report_enabled"]: return
    now = datetime.now().strftime("%H:%M")
    if now != s["daily_report_time"] or _report_at == now: return
    _report_at = now
    text = format_daily_report(sto.get_daily_stats())
    for cid in sto.get_channels():
        try: await context.bot.send_message(cid, text, parse_mode="Markdown")
        except Exception as e: print(f"report {cid}: {e}")


async def job_auto_reboot(context):
    global _reboot_at
    sto = _g(context, "store")
    s   = sto.get_settings()
    if not s["auto_reboot_enabled"]: return
    now = datetime.now().strftime("%H:%M")
    if now != s["auto_reboot_time"] or _reboot_at == now: return
    _reboot_at = now
    for cid in sto.get_channels():
        try: await context.bot.send_message(
            cid, f"↻ Auto-reboot at {s['auto_reboot_time']}. Back in ~1 min.")
        except Exception: pass
    _g(context, "controller").reboot_server()


async def job_on_startup(context):
    sto = _g(context, "store")
    if not sto.get_channels(): return
    for cid in sto.get_channels():
        try: await context.bot.send_message(cid, "✓ Bot online. Server started.")
        except Exception as e: print(f"startup {cid}: {e}")


# ── Register ──────────────────────────────────────────────────────────────────

def register_handlers(app):
    for name, fn in [
        ("start",           cmd_start),
        ("menu",            cmd_menu),
        ("status",          cmd_status),
        ("services",        cmd_services),
        ("ports",           cmd_ports),
        ("ping",            cmd_ping),
        ("restart_service", cmd_restart_service),
        ("stop_service",    cmd_stop_service),
        ("reboot",          cmd_reboot),
        ("logs",            cmd_logs),
        ("close_port",      cmd_close_port),
        ("link_channel",    cmd_link_channel),
        ("broadcast",       cmd_broadcast),
        ("report",          cmd_report),
        ("set_report_time", cmd_set_report_time),
        ("set_reboot_time", cmd_set_reboot_time),
        ("set_alerts",      cmd_set_alerts),
        ("add_ssh_key",     cmd_add_ssh_key),
        ("upload",          cmd_upload_file),
    ]:
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
