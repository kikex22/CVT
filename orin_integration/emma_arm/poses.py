#!/usr/bin/env python3
# encoding: utf-8

import os
from glob import glob
import time
import yaml
import threading
import rclpy

from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from std_msgs.msg import String, Int32MultiArray


class PosePlayer(Node):
    def __init__(self):
        super().__init__("emma_pose_player")

        # ----------------------------------
        # Publisher
        # ----------------------------------
        self.pub = self.create_publisher(
            Int32MultiArray,
            "/arm/joint_cmd",
            10
        )

        # ----------------------------------
        # Load poses YAML
        # ----------------------------------
        pkg_path = get_package_share_directory("emma_arm")

        self.declare_parameter(
            "poses_file",
            os.path.join(pkg_path, "config", "bottle_pick_pose.yaml")
        )
        self.declare_parameter(
            "poses_dir",
            os.path.join(pkg_path, "config", "poses")
        )
        poses_file = self.get_parameter("poses_file").get_parameter_value().string_value
        poses_dir = self.get_parameter("poses_dir").get_parameter_value().string_value

        self.poses = {}
        self._load_pose_file(poses_file)

        for modular_file in sorted(glob(os.path.join(poses_dir, "*.yaml"))):
            self._load_pose_file(modular_file)

        # ----------------------------------
        # Async pose state
        # ----------------------------------
        self._pose_thread = None
        self._stop_pose = False
        self._lock = threading.Lock()

        # ----------------------------------
        # Subscriber
        # ----------------------------------
        self.sub = self.create_subscription(
            String,
            "/arm/pose_cmd",
            self.pose_cb,
            10
        )

        self.get_logger().info("PosePlayer listo")
        self.get_logger().info(f"Poses cargadas: {list(self.poses.keys())}")

    def _load_pose_file(self, poses_file):
        try:
            with open(poses_file, "r") as f:
                loaded_poses = yaml.safe_load(f) or {}

            if not isinstance(loaded_poses, dict):
                raise ValueError("el contenido debe ser un mapa de poses")

            duplicates = sorted(set(self.poses).intersection(loaded_poses))
            if duplicates:
                raise ValueError(f"poses duplicadas: {duplicates}")

            self.poses.update(loaded_poses)
            self.get_logger().info(
                f"Archivo de poses cargado: {poses_file} ({len(loaded_poses)} poses)"
            )
        except Exception as e:
            self.get_logger().error(f"Error cargando poses YAML '{poses_file}': {e}")

    # =================================================
    # Callback
    # =================================================
    def pose_cb(self, msg):
        name = msg.data.strip()

        if name not in self.poses:
            self.get_logger().warn(f"[PosePlayer] Pose '{name}' no existe")
            return

        with self._lock:
            # detener pose anterior si existe
            self._stop_pose = True

            if self._pose_thread is not None and self._pose_thread.is_alive():
                self._pose_thread.join()

            self._stop_pose = False
            self._pose_thread = threading.Thread(
                target=self._run_pose,
                args=(name,),
                daemon=True
            )
            self._pose_thread.start()

    # =================================================
    # Pose runner
    # =================================================
    def _run_pose(self, name):
        pose = self.poses[name]
        duration_ms = max(
            1,
            int(pose.get("duration_ms", pose.get("speed_ms", 1)))
        )
        joint_order = pose.get("joint_order", list(pose["joints"].keys()))

        self.get_logger().info(f"Ejecutando pose: {name}")
        self.get_logger().info(f"Joint order: {joint_order}")

        for joint in joint_order:
            if self._stop_pose:
                self.get_logger().warn(f"[PosePlayer] Pose '{name}' interrumpida")
                return

            if joint not in pose["joints"]:
                continue

            pulse = pose["joints"][joint]

            cmd = Int32MultiArray()
            cmd.data = [int(joint), int(pulse), duration_ms]

            self.pub.publish(cmd)
            time.sleep(duration_ms / 1000.0)

        self.get_logger().info(f"[PosePlayer] Pose '{name}' terminada")


# =====================================================
def main(args=None):
    rclpy.init(args=args)
    node = PosePlayer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
