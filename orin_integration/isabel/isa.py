#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node

from std_msgs.msg import String, Int32MultiArray
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from od.msg import Detection2D

from core.align import AlignModule
from core.approach import ApproachModule
from core.grasp import GraspModule
from core.bin import BinModule
from core.isa_profiler import IsaProfiler
from core.arm_cam_approach import ArmCamApproachModule

import json
import shutil
import threading
import sys
import termios
import tty
import select
import textwrap
import time

try:
    from rich.console import Console
except Exception:
    Console = None


key_queue = []
running = True


def keyboard_thread():
    global running

    fd = sys.stdin.fileno()

    try:
        old = termios.tcgetattr(fd)
    except:
        print("[ISA] No TTY")
        return

    try:
        tty.setcbreak(fd)

        while running:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)

            if rlist:
                key_queue.append(sys.stdin.read(1))

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


class IsaNode(Node):

    def __init__(self):
        super().__init__('isa_node')
        self.console = self._make_console()

        # =====================================
        # STATE / PROFILER
        # =====================================
        self.state = "IDLE"
        self.profiler = IsaProfiler(self)

        # =====================================
        # DETECCION / TARGET
        # =====================================
        self.ignore_detection_until = 0.0

        self.target_ready = False
        self.last_distance = None
        self.last_offset = 0.0
        self.target_ready_distance = None
        self.target_ready_offset = 0.0

        self.target_class = "default"
        self.latest_class_name = "default"
        self.latest_class_time = 0.0
        self.recent_class_times = {}
        self.class_timeout_sec = 1.0

        self.pobjects = {"bottle", "can", "cup"}
        self.npobjects = {"bin"}

        self.last_ignore_log_time = 0.0
        self.ignore_log_interval = 1.0
        self.last_bin_filter_log_time = 0.0
        self.bin_filter_log_interval = 0.5
        self.bin_json_offset_gate = 0.055

        # =====================================
        # PENDING CLASS
        # =====================================
        self.pending_class_since = 0.0
        self.pending_class_timeout = 1.5

        # =====================================
        # BIN TAKEOVER PARAMS
        # =====================================
        self.bin_takeover_dist_threshold = 2.5
        self.pending_bin_reason = ""
        self.last_patrol_status = "unknown"

        # =====================================
        # CONTROL MODE
        # =====================================
        self.control_mode = "IDLE"
        self.profile_prepared = False

        # =====================================
        # ARM ALIGN MONITOR
        # =====================================
        self.arm_not_ok_counter = 0
        self.arm_not_ok_thresh = 3
        self.ignore_bbox_done_once = False
        self.ignore_arm_done_until = 0.0
        self.last_reset_key_time = 0.0
        self.reset_key_debounce_sec = 1.5

        # =====================================
        # PUBLISHERS
        # =====================================
        self.cmd_pub = self.create_publisher(
            Twist,
            '/controller/cmd_vel',
            10
        )

        self.patrol_pub = self.create_publisher(
            String,
            '/patrol/cmd',
            10
        )

        self.depth_mode_pub = self.create_publisher(
            String,
            '/depth_mode',
            10
        )

        self.pose_pub = self.create_publisher(
            String,
            '/arm/pose_cmd',
            10
        )

        self.joint_pub = self.create_publisher(
            Int32MultiArray,
            '/arm/joint_cmd',
            10
        )

        # =====================================
        # MODULES
        # =====================================
        self.align = AlignModule(
            self.cmd_pub,
            self.get_logger()
        )

        self.approach = ApproachModule(
            self.cmd_pub,
            self.get_logger()
        )

        self.arm_cam_approach = ArmCamApproachModule(
            self.cmd_pub,
            self.pose_pub,
            self.joint_pub,
            self.get_logger()
        )

        self.grasp = GraspModule(
            self.pose_pub,
            self.joint_pub,
            self.get_logger()
        )

        self.bin = BinModule(
            cmd_pub=self.cmd_pub,
            pose_pub=self.pose_pub,
            depth_mode_pub=self.depth_mode_pub,
            align_module=self.align,
            approach_module=self.approach,
            grasp_module=self.grasp,
            logger=self.get_logger()
        )

        # =====================================
        # SUBSCRIBERS
        # =====================================
        self.create_subscription(
            String,
            '/object_distance_json',
            self.object_cb,
            10
        )

        self.create_subscription(
            Detection2D,
            '/detections_2d',
            self.detection_cb,
            10
        )

        self.create_subscription(
            String,
            '/alignment_command',
            self.alignment_cmd_cb,
            10
        )

        self.create_subscription(
            String,
            '/arm_cam_bbox',
            self.bbox_cb,
            10
        )

        self.create_subscription(
            String,
            '/arm_cam_stop',
            self.arm_stop_cb,
            10
        )

        self.create_subscription(
            Odometry,
            '/odom',
            self.odom_cb,
            10
        )

        self.create_subscription(
            String,
            '/patrol/status',
            self.patrol_status_cb,
            10
        )

        self.create_subscription(
            String,
            '/bin_alignment',
            self.bin_alignment_cb,
            10
        )

        # =====================================
        # TIMERS
        # =====================================
        self.create_timer(0.05, self.main_loop)
        self.create_timer(0.1, self.keyboard_loop)

        self.print_help()

        if sys.stdin.isatty():
            threading.Thread(
                target=keyboard_thread,
                daemon=True
            ).start()

    # =================================================
    # HELPERS
    # =================================================
    def _make_console(self):
        if Console is None:
            return None

        return Console(
            width=self._terminal_width(),
            soft_wrap=False
        )

    def _ui_print(self, text, rich=False):
        if rich and self.console is not None:
            for line in text.split("\n"):
                self.console.print(
                    line,
                    markup=True,
                    highlight=False,
                    soft_wrap=False,
                    end="\r\n"
                )
            return

        sys.stdout.write(
            text.replace("\n", "\r\n") + "\r\n"
        )
        sys.stdout.flush()

    def _terminal_width(self):
        try:
            width = shutil.get_terminal_size((88, 24)).columns
        except Exception:
            width = 88

        return max(50, min(width, 92))

    def _wrap(self, text, indent="  "):
        return textwrap.fill(
            text,
            width=max(30, self._terminal_width() - len(indent) - 4),
            initial_indent=indent,
            subsequent_indent=indent
        )

    def _distance_label(self):
        if self.last_distance is None:
            return "none"

        return f"{self.last_distance:.2f} m"

    def _status_rows(self):
        return [
            ("state", self.state),
            ("mode", self.control_mode),
            ("target", self.target_class),
            ("ready", str(self.target_ready)),
            ("distance", self._distance_label()),
            ("offset", f"{self.last_offset:.3f}"),
            ("bin active", str(self.bin.active)),
            ("patrol", self.last_patrol_status),
        ]

    def print_status_summary(self, title="Estado ISA"):
        self.console = self._make_console()
        use_rich = self.console is not None

        lines = [
            "",
            (
                f"[bold cyan]=== ISA: {title} ===[/bold cyan]"
                if use_rich
                else f"=== ISA: {title} ==="
            ),
        ]

        for name, value in self._status_rows():
            lines.append(
                (
                    f"[dim]{name:<12}[/dim]: [white]{value}[/white]"
                    if use_rich
                    else f"{name:<12}: {value}"
                )
            )

        lines.append(
            "[cyan]==============================[/cyan]"
            if use_rich
            else "=" * 30
        )

        self._ui_print(
            "\n".join(lines),
            rich=use_rich
        )

    def print_help(self):
        self.console = self._make_console()
        use_rich = self.console is not None

        status_lines = "\n".join(
            (
                f"  [dim]{name:<12}[/dim]: [white]{value}[/white]"
                if use_rich
                else f"  {name:<12}: {value}"
            )
            for name, value in self._status_rows()
        )

        if use_rich:
            body = (
                "\n"
                "[cyan]============================================================[/cyan]\n"
                "[bold cyan] ISA[/bold cyan]\n"
                "[dim] Orquestador EMMA - UI estable para 80x24[/dim]\n"
                "[cyan]============================================================[/cyan]\n"
                "\n"
                "[bold cyan]Estado[/bold cyan]\n"
                f"{status_lines}\n\n"
                "[bold cyan]Flujo principal[/bold cyan]\n"
                "  [bold green]a[/bold green]  auto full\n"
                "  [bold green]s[/bold green]  permiso / siguiente paso\n"
                "  [bold green]r[/bold green]  reset ciclo\n"
                "  [bold green]p[/bold green]  profiler report\n"
                "  [bold green]h[/bold green]  mostrar ayuda\n"
                "  [bold green]q[/bold green]  salir\n\n"
                "[bold cyan]Bin / brazo[/bold cyan]\n"
                "  [bold yellow]b[/bold yellow]  bin directo AUTO\n"
                "  [bold yellow]t[/bold yellow]  test bin override\n"
                "  [bold yellow]x[/bold yellow]  auto joint desde cx snapshot\n"
                "  [bold yellow]y[/bold yellow]  bin joint step\n"
                "  [bold yellow]u[/bold yellow]  drop manual\n"
                "  [bold magenta]o[/bold magenta]  test pow / pow_pick directo\n\n"
                "[bold cyan]Topics clave[/bold cyan]\n"
                "  in : /object_distance_json, /detections_2d\n"
                "  in : /alignment_command, /arm_cam_bbox, /bin_alignment\n"
                "  out: /patrol/cmd, /controller/cmd_vel\n"
                "  out: /depth_mode, /arm/pose_cmd, /arm/joint_cmd\n\n"
                "[bold cyan]Notas[/bold cyan]\n"
                "  [bold green]s[/bold green] avanza segun state actual.\n"
                "  Si ve bin durante GOING_TO_BIN, pide permiso con [bold green]s[/bold green].\n"
                "[cyan]============================================================[/cyan]"
            )
        else:
            body = (
                "\n"
                "============================================================\n"
                " ISA\n"
                " Orquestador EMMA - UI estable para 80x24\n"
                "============================================================\n"
                "\n"
                "Estado\n"
                f"{status_lines}\n\n"
                "Flujo principal\n"
                "  a  auto full\n"
                "  s  permiso / siguiente paso\n"
                "  r  reset ciclo\n"
                "  p  profiler report\n"
                "  h  mostrar ayuda\n"
                "  q  salir\n\n"
                "Bin / brazo\n"
                "  b  bin directo AUTO\n"
                "  t  test bin override\n"
                "  x  auto joint desde cx snapshot\n"
                "  y  bin joint step\n"
                "  u  drop manual\n"
                "  o  test pow / pow_pick directo\n\n"
                "Topics clave\n"
                "  in : /object_distance_json, /detections_2d\n"
                "  in : /alignment_command, /arm_cam_bbox, /bin_alignment\n"
                "  out: /patrol/cmd, /controller/cmd_vel\n"
                "  out: /depth_mode, /arm/pose_cmd, /arm/joint_cmd\n\n"
                "Notas\n"
                "  s avanza segun state actual.\n"
                "  Si ve bin durante GOING_TO_BIN, pide permiso con s.\n"
                "============================================================"
            )

        self._ui_print(
            body,
            rich=use_rich
        )

    def set_state(self, new_state: str):
        if self.state == new_state:
            return

        self.profiler.state_enter(new_state)
        self.state = new_state
        self.get_logger().warn(f"STATE → {self.state}")

    def patrol_stop(self):
        self.patrol_pub.publish(
            String(data="stop")
        )

        self.get_logger().warn(
            "[ISA] PATROL STOP"
        )

    def patrol_resume(self):
        self.patrol_pub.publish(
            String(data="resume")
        )

        self.get_logger().warn(
            "[ISA] PATROL RESUME"
        )

    def patrol_route_3_point_3(self):
        self.patrol_pub.publish(
            String(data="route_3_point_3")
        )

        self.get_logger().warn(
            "[ISA] PATROL -> route_3_point_3"
        )

    def stop_base(self):
        self.cmd_pub.publish(
            Twist()
        )

    def stop_base_burst(self, count=8, interval=0.02):
        for _ in range(count):
            self.stop_base()
            time.sleep(interval)

    def set_depth_mode(self, mode: str):
        mode = mode.strip().lower()

        self.depth_mode_pub.publish(
            String(data=mode)
        )

        self.get_logger().warn(
            f"[ISA] DEPTH MODE -> {mode.upper()}"
        )

    def is_bin_recent(self):
        now = time.time()

        if self.latest_class_name == "bin":
            if (now - self.latest_class_time) <= self.class_timeout_sec:
                return True

        bin_time = self.recent_class_times.get("bin", 0.0)

        if (now - bin_time) <= self.class_timeout_sec:
            return True

        return False

    def start_bin_takeover(self, reason="bin_detected"):
        """
        ISA detecta el bin mientras patrol va hacia route_3_point_3.
        NO arranca BinModule automático.
        Primero detiene patrol y pide permiso con [s].
        """

        if self.state != "GOING_TO_BIN":
            return

        if self.bin.active:
            return

        self.pending_bin_reason = reason

        self.get_logger().warn(
            f"[ISA] VI EL BIN ({reason}) -> STOP PATROL"
        )

        self.patrol_stop()
        self.stop_base()

        self.get_logger().warn(
            "[ISA] Permiso requerido: presiona [s] para que ISA tome control del bin"
        )

        self.set_state("WAIT_BIN_TAKEOVER_CONFIRM")

    def confirm_bin_takeover(self):
        """
        Se llama cuando el usuario presiona [s] después de ver el bin.
        Aquí sí arranca BinModule.
        """

        if self.state != "WAIT_BIN_TAKEOVER_CONFIRM":
            return

        self.get_logger().warn(
            f"[ISA] PERMISO OK -> START BIN MODULE reason={self.pending_bin_reason}"
        )

        self.stop_base()

        self.bin.start(
            on_done=self._on_bin_done,
            on_state=self.set_state,
            auto_drop=(self.control_mode == "AUTO")
        )

    def _resolve_target_class(self):
        now = time.time()

        best_pobject = "default"
        best_time = 0.0

        for class_name in self.pobjects:
            class_time = self.recent_class_times.get(class_name, 0.0)

            if (now - class_time) <= self.class_timeout_sec:
                if class_time > best_time:
                    best_time = class_time
                    best_pobject = class_name

        if best_pobject != "default":
            return best_pobject

        if (now - self.latest_class_time) <= self.class_timeout_sec:
            return self.latest_class_name

        return "default"

    def _log_ignore_throttled(self, text: str):
        now = time.time()

        if now - self.last_ignore_log_time > self.ignore_log_interval:
            self.last_ignore_log_time = now
            self.get_logger().warn(text)

    def _log_bin_filter_throttled(self, text: str):
        now = time.time()

        if now - self.last_bin_filter_log_time > self.bin_filter_log_interval:
            self.last_bin_filter_log_time = now
            self.get_logger().warn(text)

    def _distance_json_label(self, data: dict):
        for key in ("class_name", "label", "class", "name"):
            value = data.get(key, "")

            if value is None:
                continue

            label = str(value).strip().lower()

            if label:
                return label

        return ""

    def _is_bin_distance_json(self, data: dict, dist: float, offset: float):
        label = self._distance_json_label(data)

        if label:
            return label in ("bin", "trash_bin", "garbage_bin")

        if not self.bin.align_found:
            return False

        # /bin_alignment uses the opposite sign from /object_distance_json.
        expected_offset = -self.bin.align_offset

        if abs(offset - expected_offset) <= self.bin_json_offset_gate:
            return True

        return False

    def _prepare_target_grasp(self):
        if self.profile_prepared:
            return

        resolved_class = self._resolve_target_class()

        if resolved_class != "default":
            self.target_class = resolved_class

        self.get_logger().warn(
            f"[ISA] PREPARE GRASP profile class={self.target_class}"
        )

        self.grasp.reset()
        self.grasp.set_profile(self.target_class)
        self.grasp.pre_grasp()

        self.profile_prepared = True

    def _classify_pending_target(self):
        resolved_class = self._resolve_target_class()

        if resolved_class == "default":
            return False

        self.target_class = resolved_class

        if self.target_class in self.npobjects:
            self.get_logger().warn(
                f"[ISA] target resultó NPOBJECT ({self.target_class}) -> queda detenido"
            )

            self.target_ready = False
            self.profile_prepared = False

            self.set_state("IDLE")
            return True

        if self.target_class not in self.pobjects:
            self.get_logger().warn(
                f"[ISA] target no agarrable ({self.target_class}) -> queda detenido"
            )

            self.target_ready = False
            self.profile_prepared = False

            self.set_state("IDLE")
            return True

        self.get_logger().warn(
            f"POBJECT confirmado class={self.target_class} — listo"
        )

        self.target_ready = True
        self.target_ready_distance = self.last_distance
        self.target_ready_offset = self.last_offset
        self.profile_prepared = False
        self.set_state("READY")
        return True

    def _wait_permission(self, wait_state: str, next_label: str):
        self.set_state(wait_state)

        self.get_logger().warn(
            f"[ISA] PERMISO: presiona [s] para {next_label}"
        )

    def _auto_or_wait(self, wait_state: str, next_label: str, next_fn):
        if self.control_mode == "AUTO":
            next_fn()
        else:
            self._wait_permission(
                wait_state,
                next_label
            )

    # =================================================
    # SUBSCRIBERS
    # =================================================
    def detection_cb(self, msg):
        try:
            class_name = str(msg.class_name).strip().lower()
        except:
            return

        if not class_name:
            return

        now = time.time()

        self.latest_class_name = class_name
        self.latest_class_time = now
        self.recent_class_times[class_name] = now

        if self.state == "READY_PENDING_CLASS":
            self._classify_pending_target()

    def bin_alignment_cb(self, msg):
        try:
            data = json.loads(msg.data)
        except Exception as e:
            self.get_logger().warn(
                f"[ISA] error leyendo /bin_alignment: {e}"
            )
            return

        self.bin.update_bin_alignment(data)

        if (
            self.state == "GOING_TO_BIN" and
            bool(data.get("found", False))
        ):
            status = str(data.get("status", "BIN_FOUND"))
            cx = int(data.get("cx", -1))
            cy = int(data.get("cy", -1))

            self.start_bin_takeover(
                reason=f"bin_alignment status={status} cx={cx} cy={cy}"
            )

    def object_cb(self, msg):
        self.profiler.mark_callback('/object_distance_json')

        if time.time() < self.ignore_detection_until:
            return

        try:
            data = json.loads(msg.data)
            dist = float(data["distance"])
            offset = float(data.get("x_offset", 0.0))
        except:
            return

        if self.bin.active:

            if self._is_bin_distance_json(data, dist, offset):
                self.last_distance = dist
                self.last_offset = offset
                self.bin.update_distance(dist, offset)
            else:
                self._log_bin_filter_throttled(
                    f"[ISA][BIN_FILTER] ignoro distance_json dist={dist:.3f} "
                    f"offset={offset:.3f} align_found={self.bin.align_found} "
                    f"bin_offset={self.bin.align_offset:.3f}"
                )

            return

        self.last_distance = dist
        self.last_offset = offset

        self.approach.update_distance(dist)
        self.align.update_offset(offset)
        self.bin.update_distance(dist, offset)

        # =====================================
        # BIN DETECTADO MIENTRAS PATROL VA AL BIN
        # =====================================
        if self.state == "GOING_TO_BIN":

            if self.is_bin_recent() and dist < self.bin_takeover_dist_threshold:

                self.start_bin_takeover(
                    reason=f"vision dist={dist:.2f}"
                )

                return

        # =====================================
        # DETECCION NORMAL:
        # Primero paramos patrol y luego confirmamos clase.
        # =====================================
        if self.state == "IDLE" and dist < 2.0:
            resolved_class = self._resolve_target_class()

            if resolved_class in self.npobjects:
                self._log_ignore_throttled(
                    f"[ISA] ignoro NPOBJECT cercano class={resolved_class} "
                    f"dist={dist:.3f}"
                )
                return

            self.get_logger().warn(
                f"[ISA] OBJETO CERCA dist={dist:.3f} -> STOP PATROL"
            )

            self.patrol_stop()
            self.stop_base()

            self.target_ready = False
            self.profile_prepared = False
            self.pending_class_since = time.time()

            if self._classify_pending_target():
                return

            self.get_logger().warn(
                "[ISA] esperando clase desde /detections_2d..."
            )

            self.set_state("READY_PENDING_CLASS")
            return

    def alignment_cmd_cb(self, msg):
        self.profiler.mark_callback('/alignment_command')

        raw = msg.data.strip().upper()
        cmd = raw.split(":")[0]

        if cmd in ("OK", "MOVE_LEFT", "MOVE_RIGHT"):
            self.align.update_arm_cmd(cmd)
            self.grasp.update_arm_cmd(cmd)
            self.arm_cam_approach.update_arm_cmd(raw)

    def bbox_cb(self, msg):
        try:
            data = json.loads(msg.data)
            area = float(data["area"])
            self.approach.update_area(area)
            self.arm_cam_approach.update_bbox(data)
        except:
            pass

    def arm_stop_cb(self, msg):
        if msg.data != "STOP":
            return

        if self.state == "APPROACH_BBOX":
            self.approach.update_arm_stop()

    def odom_cb(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        self.approach.update_odom(x, y)

    def patrol_status_cb(self, msg):
        status = msg.data.strip().lower()
        self.last_patrol_status = status

        if status == "bin_reached" and self.state == "GOING_TO_BIN":

            self.pending_bin_reason = "patrol_bin_reached"

            self.get_logger().warn(
                "[ISA] PATROL llegó al punto del bin -> STOP + esperando permiso"
            )

            self.patrol_stop()
            self.stop_base()

            self.get_logger().warn(
                "[ISA] Permiso requerido: presiona [s] para que ISA tome control del bin"
            )

            self.set_state("WAIT_BIN_TAKEOVER_CONFIRM")

    # =================================================
    # MAIN LOOP
    # =================================================
    def main_loop(self):
        now = time.time()

        if self.state == "READY_PENDING_CLASS":

            if self._classify_pending_target():
                return

            if now - self.pending_class_since > self.pending_class_timeout:

                self.get_logger().warn(
                    "[ISA] timeout esperando clase -> queda detenido en IDLE"
                )

                self.target_ready = False
                self.profile_prepared = False

                self.set_state("IDLE")
                return

        if self.bin.active:
            self.bin.step(now)
        else:
            if self.align.active:
                self.align.step()

        if self.grasp.aligning:
            self.grasp.step(now)

        if self.state == "APPROACH_BBOX":
            if self._try_arm_cam_lost_recovery():
                return

            cmd = self.grasp.last_align_cmd

            if cmd in ("MOVE_LEFT", "MOVE_RIGHT"):
                self.arm_not_ok_counter += 1
            else:
                self.arm_not_ok_counter = 0

            if self.arm_not_ok_counter >= self.arm_not_ok_thresh:
                self.get_logger().warn(
                    f"[ISA] ARM CAM LOST ALIGN ({cmd})"
                )

                self.arm_not_ok_counter = 0

                self.approach.pause()
                self.grasp.last_align_cmd = None

                self.grasp.start_arm_align(
                    on_done=self._on_micro_align_done
                )

                self.set_state("MICRO_ALIGNING")

    # =================================================
    # BIN ENTRYPOINTS
    # =================================================
    def start_bin_test_override(self):
        self.get_logger().warn(">>> TEST BIN OVERRIDE [t]")

        self.stop_base()
        self.align.stop()
        self.approach.stop()
        self.arm_cam_approach.stop()
        self.bin.reset()

        self.control_mode = "AUTO"
        self.target_ready = False
        self.profile_prepared = False
        self.arm_not_ok_counter = 0

        self.patrol_stop()

        self.bin.start(
            on_done=self._on_bin_done,
            on_state=self.set_state,
            auto_drop=False
        )

    def start_bin_direct_auto(self):
        self.get_logger().warn(">>> BIN DIRECT AUTO [b]")

        self.stop_base()
        self.align.stop()
        self.approach.stop()
        self.arm_cam_approach.stop()
        self.bin.reset()

        self.control_mode = "AUTO"
        self.target_ready = False
        self.profile_prepared = False
        self.arm_not_ok_counter = 0

        self.patrol_stop()

        self.bin.start(
            on_done=self._on_bin_done,
            on_state=self.set_state,
            auto_drop=True
        )

    def start_bin_after_grasp(self):
        self.bin.start(
            on_done=self._on_bin_done,
            on_state=self.set_state,
            auto_drop=(self.control_mode == "AUTO")
        )

    def _on_bin_done(self):
        self.get_logger().warn("[ISA] BIN FLOW DONE")

        self.finish_cycle()

    # =================================================
    # ARM TEST ENTRYPOINTS
    # =================================================
    def start_pow_branch_test(self):
        self.get_logger().warn(">>> TEST POW / POW_PICK DIRECTO [o]")

        self.stop_base()
        self.align.stop()
        self.approach.stop()
        self.arm_cam_approach.stop()
        self.bin.reset()

        self.control_mode = "AUTO"
        self.target_class = "bottle"
        self.target_ready = True
        self.profile_prepared = True
        self.ignore_bbox_done_once = True
        self.arm_not_ok_counter = 0
        self.grasp.last_align_cmd = None

        self.patrol_stop()

        started = self.arm_cam_approach.start_pow_test(
            on_done=self._on_front_lying_arm_done
        )

        if started:
            self.set_state("ARM_FRONT_LYING_APPROACH")
            return

        self.ignore_bbox_done_once = False
        self.set_state("IDLE")

    # =================================================
    # OBJECT FLOW
    # =================================================
    def start_cycle(self, mode: str):
        if self.state not in ("READY", "DONE"):
            self.get_logger().warn(
                f"[ISA] no puedo empezar desde state={self.state}"
            )
            return

        if not self.target_ready or self.last_distance is None:
            self.get_logger().warn(
                "[ISA] no hay objeto listo todavia"
            )
            return

        resolved_class = self._resolve_target_class()

        if resolved_class != "default":
            self.target_class = resolved_class

        if self.target_class in self.npobjects:
            self.get_logger().warn(
                f"[ISA] START CANCELADO: target es NPOBJECT ({self.target_class})"
            )

            self.target_ready = False
            self.profile_prepared = False

            self.set_state("IDLE")
            return

        if self.target_class not in self.pobjects:
            self.get_logger().warn(
                f"[ISA] START CANCELADO: clase no agarrable ({self.target_class})"
            )

            self.target_ready = False
            self.profile_prepared = False

            self.set_state("IDLE")
            return

        self.control_mode = mode

        self.get_logger().warn(
            f">>> START CYCLE mode={self.control_mode} class={self.target_class}"
        )

        self._prepare_target_grasp()
        self.arm_cam_approach.reset_tracking()
        self.profiler.cycle_start()
        self.arm_not_ok_counter = 0

        self.start_align1()

    def execute_final_grasp(self):
        self.get_logger().warn(
            f">>> FINAL GRASP class={self.target_class}"
        )

        self.grasp.grasp_final()

        time.sleep(2.0)

        self.get_logger().warn(
            "[ISA] FINAL GRASP DONE -> PATROL route_3_point_3"
        )

        self.patrol_route_3_point_3()

        self.set_state("GOING_TO_BIN")

    def start_align1(self):
        self.get_logger().warn(">>> START ALIGN 1")
        self.profiler.mark_publish('/align_trigger')

        self.align.start(
            mode="depth",
            on_done=self._on_align1_done
        )

        self.set_state("ALIGNING_1")

    def start_approach_dist(self):
        self.get_logger().warn(">>> START APPROACH DIST")
        self.profiler.mark_publish('/approach_trigger')

        if self.target_ready_distance is not None:
            self.last_distance = self.target_ready_distance
            self.last_offset = self.target_ready_offset
            self.approach.update_distance(self.target_ready_distance)
            self.align.update_offset(self.target_ready_offset)
            self.get_logger().warn(
                f"[ISA] APPROACH_DIST usa target snapshot "
                f"dist={self.target_ready_distance:.3f} "
                f"offset={self.target_ready_offset:.3f}"
            )

        self.approach.start_dist(
            target_distance=0.70,
            on_target_reached=self._on_target_reached
        )

        self.set_state("APPROACH_DIST")

    def start_align2(self):
        self.get_logger().warn(">>> START ALIGN 2")
        self.profiler.mark_publish('/align_trigger')

        self.align.start(
            mode="depth",
            on_done=self._on_align2_done
        )

        self.set_state("ALIGNING_2")

    def start_align3(self):
        self.get_logger().warn(">>> START ALIGN 3")
        self.profiler.mark_publish('/align_trigger')

        self.align.start(
            mode="arm",
            on_done=self._on_align3_done
        )

        self.set_state("ALIGNING_3")

    def start_pre_bbox_check(self):
        self.get_logger().warn(">>> VERIFICANDO ARM ANTES DE BBOX")

        self.grasp.last_align_cmd = None
        self.align.latest_arm_cmd = None
        self.arm_not_ok_counter = 0
        self.arm_cam_approach.reset_tracking()

        self.grasp.start_arm_align(
            on_done=self._on_pre_bbox_align_done
        )

        self.set_state("PRE_BBOX_ALIGNING")

    def start_object_approach_after_pre_bbox(self):
        if self.target_class in ("bottle", "plastic_bottle"):
            self.get_logger().warn(
                "[ISA] ARM CAM sample antes decision PRE BBOX: "
                + self.arm_cam_approach.describe_sample()
            )

            if self._try_front_lying_arm_approach("pre BBOX"):
                return

        self.start_bbox_approach()

    def start_bbox_approach(self):
        self.get_logger().warn(">>> START BBOX APPROACH")

        self.grasp.last_align_cmd = None
        self.arm_not_ok_counter = 0

        if self.target_class in ("bottle", "plastic_bottle"):
            self.get_logger().warn(
                "[ISA] ARM CAM sample antes BBOX: "
                + self.arm_cam_approach.describe_sample()
            )

        self.approach.start_bbox(
            on_done=self._on_approach_bbox_done
        )

        self.set_state("APPROACH_BBOX")

    def _try_front_lying_arm_approach(self, source):
        if self.target_class not in ("bottle", "plastic_bottle"):
            return False

        if not self.arm_cam_approach.is_front_lying_candidate():
            return False

        self.get_logger().warn(
            "[ISA] ARM CAM front_lying detectado "
            f"({source}) -> approach frontal + pow: "
            + self.arm_cam_approach.describe_sample()
        )

        self.ignore_bbox_done_once = True
        self.approach.stop()
        self.stop_base()
        self.grasp.last_align_cmd = None
        self.arm_not_ok_counter = 0

        started = self.arm_cam_approach.start_front_lying(
            on_done=self._on_front_lying_arm_done
        )

        if started:
            self.set_state("ARM_FRONT_LYING_APPROACH")
            return True

        self.ignore_bbox_done_once = False
        return False

    def _try_arm_cam_lost_recovery(self):
        if self.target_class not in ("bottle", "plastic_bottle"):
            return False

        if not self.arm_cam_approach.should_recover_lost_near_object():
            return False

        self.get_logger().warn(
            "[ISA] ARM CAM bbox perdido cerca -> reverse recovery"
        )

        self.ignore_bbox_done_once = True
        self.approach.stop()
        self.stop_base()
        self.grasp.last_align_cmd = None
        self.arm_not_ok_counter = 0

        started = self.arm_cam_approach.start_lost_recovery(
            on_done=self._on_arm_cam_lost_recovery_done
        )

        if started:
            self.set_state("ARM_CAM_LOST_RECOVERY")
            return True

        self.ignore_bbox_done_once = False
        return False

    def start_final_check(self):
        self.get_logger().warn(">>> VERIFICANDO ARM PARA GRASP FINAL")

        self.grasp.last_align_cmd = None
        self.arm_not_ok_counter = 0

        self.grasp.start_arm_align(
            on_done=self._on_final_align_done
        )

        self.set_state("FINAL_MICRO_ALIGN")

    def finish_cycle(self):
        self.get_logger().warn(">>> CYCLE DONE")

        self.profiler.cycle_end()
        self.ignore_detection_until = time.time() + 8.0

        self.target_ready = False
        self.last_distance = None
        self.last_offset = 0.0
        self.target_ready_distance = None
        self.target_ready_offset = 0.0

        self.target_class = "default"
        self.latest_class_name = "default"
        self.latest_class_time = 0.0
        self.recent_class_times.clear()

        self.control_mode = "IDLE"
        self.profile_prepared = False
        self.arm_not_ok_counter = 0

        self.pending_bin_reason = ""

        self.bin.reset()
        self.arm_cam_approach.stop()
        self.arm_cam_approach.reset_tracking()
        self.set_depth_mode("normal")

        self.patrol_stop()

        self.set_state("DONE")

    # =================================================
    # CALLBACKS DE MODULOS
    # =================================================
    def _on_align1_done(self):
        self.stop_base()
        self.get_logger().warn("ALIGN 1 OK")

        self._auto_or_wait(
            "WAIT_APPROACH_DIST_CONFIRM",
            "APPROACH DIST",
            self.start_approach_dist
        )

    def _on_target_reached(self):
        self.stop_base()
        self.get_logger().warn("TARGET DISTANCE REACHED")

        self._auto_or_wait(
            "WAIT_ALIGN_2_CONFIRM",
            "ALIGN 2",
            self.start_align2
        )

    def _on_align2_done(self):
        self.stop_base()
        self.get_logger().warn("ALIGN 2 OK")

        self._auto_or_wait(
            "WAIT_ALIGN_3_CONFIRM",
            "ALIGN 3",
            self.start_align3
        )

    def _on_align3_done(self):
        self.stop_base()
        self.get_logger().warn("ALIGN 3 OK")

        self.grasp.last_align_cmd = None
        self.align.latest_arm_cmd = None

        self._auto_or_wait(
            "WAIT_PRE_BBOX_CONFIRM",
            "PRE BBOX ARM CHECK",
            self.start_pre_bbox_check
        )

    def _on_pre_bbox_align_done(self):
        self.get_logger().warn("PRE BBOX ALIGN OK")

        self._auto_or_wait(
            "WAIT_BBOX_APPROACH_CONFIRM",
            "BBOX/POW APPROACH",
            self.start_object_approach_after_pre_bbox
        )

    def _on_front_lying_arm_done(self, reason="unknown"):
        self.stop_base()

        if time.time() < self.ignore_arm_done_until:
            self.get_logger().warn(
                f"[ISA] ignoro FRONT_LYING done viejo reason={reason}"
            )
            self.stop_base_burst()
            return

        if self.state != "ARM_FRONT_LYING_APPROACH":
            self.get_logger().warn(
                f"[ISA] ignoro FRONT_LYING done state={self.state} reason={reason}"
            )
            self.stop_base_burst()
            return

        self.ignore_bbox_done_once = False
        self.get_logger().warn(
            f"[ISA] FRONT_LYING ARM DONE reason={reason}"
        )

        if reason == "pow_pick":
            self.get_logger().warn(
                "[ISA] FRONT_LYING POW_PICK DONE -> PATROL route_3_point_3"
            )
            self.patrol_route_3_point_3()
            self.set_state("GOING_TO_BIN")
            return

        if reason == "pow":
            self.set_state("FRONT_LYING_POW_DONE")
            return

        self.set_state("FRONT_LYING_ABORTED")

    def _on_arm_cam_lost_recovery_done(self, reason="unknown"):
        self.stop_base()
        self.ignore_bbox_done_once = False
        self.get_logger().warn(
            f"[ISA] ARM CAM LOST RECOVERY DONE reason={reason}"
        )

        if reason == "recovered":
            self.start_bbox_approach()
            return

        self.set_state("ARM_CAM_LOST_ABORTED")

    def _on_micro_align_done(self):
        self.get_logger().warn("MICRO ALIGN DONE")

        self.grasp.last_align_cmd = None
        self.arm_not_ok_counter = 0

        if self.state == "MICRO_ALIGNING":
            self.approach.resume()
            self.set_state("APPROACH_BBOX")

    def _on_approach_bbox_done(self):
        if self.ignore_bbox_done_once:
            self.ignore_bbox_done_once = False
            self.get_logger().warn(
                f"[ISA] ignoro BBOX done cancelado state={self.state}"
            )
            return

        if self.state != "APPROACH_BBOX":
            self.get_logger().warn(
                f"[ISA] ignoro BBOX done viejo state={self.state}"
            )
            return

        self.stop_base()
        self.get_logger().warn("APPROACH BBOX COMPLETO")

        self._auto_or_wait(
            "WAIT_FINAL_ALIGN_CONFIRM",
            "FINAL ARM CHECK",
            self.start_final_check
        )

    def _on_final_align_done(self):
        self.get_logger().warn("FINAL ALIGN OK")

        self.grasp.last_align_cmd = None

        if self.control_mode == "AUTO":
            self.execute_final_grasp()
        else:
            self._wait_permission(
                "WAIT_GRASP_CONFIRM",
                "GRASP FINAL"
            )

    # =================================================
    # RESET
    # =================================================
    def reset_cycle(self):
        self.get_logger().warn("RESTARTING ISA")

        self.ignore_arm_done_until = time.time() + 2.0

        self.stop_base()
        self.set_depth_mode("normal")

        self.align.stop()
        self.approach.stop()
        self.arm_cam_approach.stop()
        self.bin.reset()

        self.grasp.reset()
        self.grasp.set_profile("default")
        self.grasp.pre_grasp()

        self.ignore_detection_until = 0.0

        self.target_ready = False
        self.last_distance = None
        self.last_offset = 0.0
        self.target_ready_distance = None
        self.target_ready_offset = 0.0

        self.target_class = "default"
        self.latest_class_name = "default"
        self.latest_class_time = 0.0
        self.recent_class_times.clear()

        self.control_mode = "IDLE"
        self.profile_prepared = False
        self.arm_not_ok_counter = 0

        self.pending_class_since = 0.0
        self.pending_bin_reason = ""

        self.profiler.reset()
        self.arm_cam_approach.reset_tracking()

        self.patrol_stop()
        self.stop_base_burst()

        self.set_state("IDLE")

    # =================================================
    # KEYBOARD
    # =================================================
    def keyboard_loop(self):
        global key_queue, running

        if not key_queue:
            return

        ch = key_queue.pop(0)

        if ch == 'q':
            self.get_logger().warn("CERRANDO ISA")
            running = False

            self.stop_base()
            self.destroy_node()
            rclpy.shutdown()
            return

        if ch == 'p':
            self.profiler.report()
            return

        if ch == 'h':
            self.print_help()
            return

        if ch == 'r':
            now = time.time()
            key_queue[:] = [
                queued_ch for queued_ch in key_queue
                if queued_ch != 'r'
            ]

            if (now - self.last_reset_key_time) < self.reset_key_debounce_sec:
                self.get_logger().warn("[ISA] reset ignorado por debounce")
                return

            self.last_reset_key_time = now
            self.reset_cycle()
            return

        if ch == 't':
            self.start_bin_test_override()
            return

        if ch == 'b':
            self.start_bin_direct_auto()
            return

        if ch == 'o':
            self.start_pow_branch_test()
            return

        if ch == 'x':
            result = self.bin.auto_joint_from_cx_snapshot()
            self.get_logger().warn(
                f"[ISA] BIN AUTO CX RESULT={result}"
            )
            return

        if ch == 'y':
            result = self.bin.manual_joint_step_once()
            self.get_logger().warn(
                f"[ISA] BIN DROP STEP RESULT={result}"
            )
            return

        if ch == 'u':
            self.get_logger().warn(
                "[ISA] permiso manual [u] -> DROP"
            )

            self.bin.drop()
            return

        if ch == 'a':
            if self.state in ("READY", "DONE"):
                self.start_cycle(mode="AUTO")
            else:
                self.get_logger().warn(
                    f"[ISA] no puedo iniciar AUTO desde state={self.state}"
                )
            return

        if ch == 's':
            if self.state in ("READY", "DONE"):
                self.start_cycle(mode="PERMISSION")
                return

            if self.state == "WAIT_APPROACH_DIST_CONFIRM":
                self.start_approach_dist()
                return

            if self.state == "WAIT_ALIGN_2_CONFIRM":
                self.start_align2()
                return

            if self.state == "WAIT_ALIGN_3_CONFIRM":
                self.start_align3()
                return

            if self.state == "WAIT_PRE_BBOX_CONFIRM":
                self.start_pre_bbox_check()
                return

            if self.state == "WAIT_BBOX_APPROACH_CONFIRM":
                self.start_object_approach_after_pre_bbox()
                return

            if self.state == "WAIT_FINAL_ALIGN_CONFIRM":
                self.start_final_check()
                return

            if self.state == "WAIT_GRASP_CONFIRM":
                self.execute_final_grasp()
                return

            if self.state == "WAIT_BIN_TAKEOVER_CONFIRM":
                self.confirm_bin_takeover()
                return

            if self.state == "GOING_TO_BIN":
                self.get_logger().warn(
                    "[ISA] todavía voy hacia el bin. Espera detección o bin_reached."
                )
                return

            self.get_logger().warn(
                f"[ISA] [s] sin accion para state={self.state}"
            )
            return


def main():
    rclpy.init()
    node = IsaNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        global running
        running = False

        try:
            node.stop_base()
            node.destroy_node()
        except:
            pass

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
