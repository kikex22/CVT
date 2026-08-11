#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from std_msgs.msg import String, Int32MultiArray
import time


class GraspModule:

    def __init__(self, pose_pub, joint_pub, logger):

        self.pose_pub  = pose_pub
        self.joint_pub = joint_pub
        self.logger    = logger

        self.grasp_profiles = {
            "bottle": {
                "pre_grasp_pose": "bottle.pre_grasp",
                "final_grasp_pose": "bottle.grip",
                "lift_pose": "bottle.lift",
                "joint1_start": 500,
                "align_step": 20,
                "align_wait_sec": 3,
            },

            "can": {
                "pre_grasp_pose": "can.pre_grasp",
                "final_grasp_pose": "can.grip",
                "lift_pose": "can.lift",
                "joint1_start": 500,
                "align_step": 20,
                "align_wait_sec": 3,
            },

            "cup": {
                "pre_grasp_pose": "cup.pre_grasp",
                "final_grasp_pose": "cup.grip",
                "lift_pose": "cup.lift",
                "joint1_start": 500,
                "align_step": 20,
                "align_wait_sec": 3,
            },

            "default": {
                "pre_grasp_pose": "lateral_log_pre",
                "final_grasp_pose": "lateral_grip",
                "lift_pose": "bottle_lift",
                "joint1_start": 500,
                "align_step": 20,
                "align_wait_sec": 3,
            },
        }

        self.current_profile_name = "default"

        self.pre_grasp_pose   = "bottle_pre"
        self.final_grasp_pose = "lateral_grip"
        self.lift_pose        = "lateral_log_lift"

        self.align_distance_threshold = 0.75
        self.align_step               = 20
        self.align_wait_sec           = 3

        self.lift_delay_sec = 2.0

        self.pre_grasp_sent   = False
        self.final_grasp_sent = False

        self.joint1_pulse = 500

        self.arm_align_active = False
        self.aligning         = False
        self.last_align_cmd   = None
        self.last_move_time   = None

        self._on_arm_align_done = None

        # =================================================
        # BIN DROP AUTO CX → JOINT1
        # =================================================
        # Rango seguro inicial segun pruebas reales:
        # cx≈265 -> j1≈540
        # cx≈330 -> j1≈510
        # cx≈363 -> j1≈500
        # cx≈390 -> j1≈480
        # cx≈460 -> j1≈440
        self.bin_drop_j1_min = 440
        self.bin_drop_j1_max = 540

    def reset(self):

        self.pre_grasp_sent   = False
        self.final_grasp_sent = False

        profile = self.grasp_profiles.get(
            self.current_profile_name,
            self.grasp_profiles["default"]
        )

        self.joint1_pulse = profile.get("joint1_start", 500)

        self.arm_align_active = False
        self.aligning         = False
        self.last_align_cmd   = None
        self.last_move_time   = None
        self._on_arm_align_done = None

        self.logger.warn("[GRASP] reset")

    def set_profile(self, class_name: str):

        key = str(class_name).strip().lower()

        aliases = {
            "plastic_bottle": "bottle",
            "bottle": "bottle",
            "can": "can",
            "minican": "can",
            "object": "default",
        }

        key = aliases.get(key, key)

        if key not in self.grasp_profiles:

            self.logger.warn(
                f"[GRASP] profile '{key}' no existe, usando default"
            )

            key = "default"

        profile = self.grasp_profiles[key]

        self.current_profile_name = key

        self.pre_grasp_pose = profile.get(
            "pre_grasp_pose",
            "bottle_pre"
        )

        self.final_grasp_pose = profile.get(
            "final_grasp_pose",
            "common_grip"
        )

        self.lift_pose = profile.get(
            "lift_pose",
            "lateral_log_lift"
        )

        self.joint1_pulse = profile.get("joint1_start", 500)
        self.align_step = profile.get("align_step", 20)
        self.align_wait_sec = profile.get("align_wait_sec", 3)

        self.logger.warn(
            f"[GRASP] profile={key} "
            f"pre={self.pre_grasp_pose} "
            f"grip={self.final_grasp_pose} "
            f"lift={self.lift_pose}"
        )

    def pre_grasp(self):

        if self.pre_grasp_sent:
            return

        self.pre_grasp_sent = True

        self.pose_pub.publish(
            String(data=self.pre_grasp_pose)
        )

        self.logger.info(
            f"[GRASP] pre_grasp → {self.pre_grasp_pose}"
        )

    def grasp_final(self):

        if self.final_grasp_sent:
            return

        self.final_grasp_sent = True

        self.pose_pub.publish(
            String(data=self.final_grasp_pose)
        )

        self.logger.info(
            f"[GRASP] grasp_final → {self.final_grasp_pose}"
        )

        time.sleep(self.lift_delay_sec)

        if self.lift_pose:

            self.pose_pub.publish(
                String(data=self.lift_pose)
            )

            self.logger.info(
                f"[GRASP] lift → {self.lift_pose}"
            )


    def start_arm_align(self, on_done):

        self.arm_align_active   = True
        self.aligning           = True
        self.last_align_cmd     = None
        self.last_move_time     = None
        self._on_arm_align_done = on_done

        self.logger.warn("[GRASP] start_arm_align")

    def update_arm_cmd(self, cmd: str):

        self.last_align_cmd = cmd

    def step(self, now_sec: float):

        if not self.aligning:
            return

        if self.last_align_cmd is None:
            return

        if self.last_move_time is not None:

            if (now_sec - self.last_move_time) < self.align_wait_sec:
                return

        cmd = self.last_align_cmd

        if cmd == "OK":

            self.logger.info("[GRASP] ARM ALIGN OK")

            self.aligning         = False
            self.arm_align_active = False

            if self._on_arm_align_done:
                self._on_arm_align_done()

            return

        if cmd == "MOVE_LEFT":

            self.joint1_pulse = min(
                self.joint1_pulse + self.align_step,
                1000
            )

            self.logger.info(
                f"[GRASP] MOVE_LEFT → joint1={self.joint1_pulse}"
            )

        elif cmd == "MOVE_RIGHT":

            self.joint1_pulse = max(
                self.joint1_pulse - self.align_step,
                0
            )

            self.logger.info(
                f"[GRASP] MOVE_RIGHT → joint1={self.joint1_pulse}"
            )

        self._send_joint1(self.joint1_pulse)
        self.last_move_time = now_sec

    # =================================================
    # BIN DROP ALIGN — semi manual
    # ISA/BinModule llama esto solamente cuando tú mandas "y".
    # Por ahora BASE tambien mueve joint, no mueve carro.
    # =================================================
    def bin_drop_step_once(self, bin_status: str):

        status = str(bin_status).strip()

        if status == "BIN_CENTER":

            self.logger.warn(
                "[GRASP][BIN_DROP] BIN_CENTER → listo para soltar"
            )

            return "READY_DROP"

        if status == "BIN_BASE_LEFT":

            self.joint1_pulse = min(
                self.joint1_pulse + self.align_step,
                1000
            )

            self.logger.warn(
                f"[GRASP][BIN_DROP] BIN_BASE_LEFT → joint1={self.joint1_pulse}"
            )

            self._send_joint1(self.joint1_pulse)
            return "MOVED_LEFT"

        if status == "BIN_BASE_RIGHT":

            self.joint1_pulse = max(
                self.joint1_pulse - self.align_step,
                0
            )

            self.logger.warn(
                f"[GRASP][BIN_DROP] BIN_BASE_RIGHT → joint1={self.joint1_pulse}"
            )

            self._send_joint1(self.joint1_pulse)
            return "MOVED_RIGHT"

        if status == "BIN_ARM_LEFT":

            self.joint1_pulse = min(
                self.joint1_pulse + self.align_step,
                1000
            )

            self.logger.warn(
                f"[GRASP][BIN_DROP] BIN_ARM_LEFT → joint1={self.joint1_pulse}"
            )

            self._send_joint1(self.joint1_pulse)
            return "MOVED_LEFT"

        if status == "BIN_ARM_RIGHT":

            self.joint1_pulse = max(
                self.joint1_pulse - self.align_step,
                0
            )

            self.logger.warn(
                f"[GRASP][BIN_DROP] BIN_ARM_RIGHT → joint1={self.joint1_pulse}"
            )

            self._send_joint1(self.joint1_pulse)
            return "MOVED_RIGHT"

        self.logger.warn(
            f"[GRASP][BIN_DROP] status desconocido/no usable: {status}"
        )

        return "NO_ACTION"

    # =================================================
    # BIN DROP AUTO — snapshot cx → joint1
    # =================================================
    def bin_drop_estimate_joint1_from_cx(self, cx: int):
        """
        Calcula joint1 a partir de un cx tomado UNA sola vez antes
        de mover el brazo. No debe usarse en loop cerrado mientras
        el brazo entra en el frame porque el bbox del bin se recorta.
        """

        try:
            cx = int(cx)
        except:
            self.logger.warn(
                f"[GRASP][BIN_DROP_AUTO] cx invalido: {cx}"
            )
            return None

        # Tabla inicial calibrada con pruebas reales:
        # cx≈265 -> j1≈540
        # cx≈330 -> j1≈510
        # cx≈363 -> j1≈500
        # cx≈390 -> j1≈480
        # cx≈460 -> j1≈440
        if cx < 290:
            target = 540
        elif cx < 345:
            target = 510
        elif cx < 375:
            target = 500
        elif cx < 410:
            target = 480
        elif cx < 440:
            target = 460
        else:
            target = 440

        target = max(
            self.bin_drop_j1_min,
            min(target, self.bin_drop_j1_max)
        )

        return target

    def bin_drop_auto_joint1_from_cx(self, cx: int):
        """
        Mueve joint1 directo usando el cx snapshot del bin.
        Esta funcion es para prueba con tecla, no para corregir en loop.
        """

        target = self.bin_drop_estimate_joint1_from_cx(cx)

        if target is None:
            return "NO_ACTION"

        self.joint1_pulse = target
        self._send_joint1(self.joint1_pulse)

        self.logger.warn(
            f"[GRASP][BIN_DROP_AUTO] snapshot cx={int(cx)} → joint1={self.joint1_pulse}"
        )

        return "AUTO_MOVED"

    def drop_object(self, drop_pose: str = "drop"):

        self.pose_pub.publish(
            String(data=drop_pose)
        )

        self.logger.warn(
            f"[GRASP][BIN_DROP] drop pose → {drop_pose}"
        )

    def _send_joint1(self, pulse: int):

        msg = Int32MultiArray()
        msg.data = [1, pulse, 1]

        self.joint_pub.publish(msg)
