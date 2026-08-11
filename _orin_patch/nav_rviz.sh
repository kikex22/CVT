#!/bin/bash
# Nav2 limpio con RViz y sin patrol.
SESSION=nav_rviz

# =========================
# ROS2 Humble
# =========================
source /opt/ros/humble/setup.bash
source ~/Documents/orbbec_ws/install/setup.bash
source ~/emma/install/setup.bash

# =========================
# ALWAYS START CLEAN
# =========================
timeout 1 ros2 topic pub --once /controller/cmd_vel geometry_msgs/msg/Twist "{}" >/tmp/c10_stop_cmd.log 2>&1 || true
timeout 1 ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}" >>/tmp/c10_stop_cmd.log 2>&1 || true

tmux has-session -t $SESSION 2>/dev/null && {
  echo "Killing previous tmux session: $SESSION"
  tmux kill-session -t $SESSION
}
tmux has-session -t nav 2>/dev/null && {
  echo "Killing previous tmux session: nav"
  tmux kill-session -t nav
}

for pattern in \
  "[r]os2 launch carolina nav.launch.py" \
  "[r]os2 launch slam carolina.launch.py" \
  "[r]os_robot_controller" \
  "[o]dom_publisher" \
  "[o]dom_publisher_nav2" \
  "[e]kf_node" \
  "[s]ervo_controller" \
  "[s]llidar_node" \
  "[s]lam_toolbox" \
  "[a]mcl" \
  "[b]t_navigator" \
  "[c]ontroller_server" \
  "[p]lanner_server" \
  "[b]ehavior_server" \
  "[s]moother_server" \
  "[w]aypoint_follower" \
  "[v]elocity_smoother" \
  "[l]ifecycle_manager" \
  "[c]md_vel_relay" \
  "[r]os2 launch isabel emma.launch.py" \
  "[e]mma_arm_core" \
  "[e]mma_arm_poses"
do
  pkill -TERM -f "$pattern" 2>/dev/null || true
done
sleep 2
for pattern in \
  "[r]os2 launch carolina nav.launch.py" \
  "[r]os2 launch slam carolina.launch.py" \
  "[r]os_robot_controller" \
  "[o]dom_publisher" \
  "[o]dom_publisher_nav2" \
  "[e]kf_node" \
  "[s]ervo_controller" \
  "[s]llidar_node" \
  "[s]lam_toolbox" \
  "[a]mcl" \
  "[b]t_navigator" \
  "[c]ontroller_server" \
  "[p]lanner_server" \
  "[b]ehavior_server" \
  "[s]moother_server" \
  "[w]aypoint_follower" \
  "[v]elocity_smoother" \
  "[l]ifecycle_manager" \
  "[c]md_vel_relay" \
  "[r]os2 launch isabel emma.launch.py" \
  "[e]mma_arm_core" \
  "[e]mma_arm_poses"
do
  pkill -KILL -f "$pattern" 2>/dev/null || true
done

LIDAR_PORT="/dev/serial/by-path/platform-3610000.usb-usb-0:2.3.4:1.0-port0"
for _ in 1 2 3 4 5 6 7 8
do
  [ -e "$LIDAR_PORT" ] && break
  sleep 1
done

if [ ! -e "$LIDAR_PORT" ]; then
  echo "ERROR: LIDAR no existe en $LIDAR_PORT. Revisa ch34x/USB antes de iniciar Nav2."
  exit 1
fi

# =========================
# Create tmux session
# =========================
tmux new-session -d -s $SESSION

# =========================================================
# Pane 0 → CAROLINA (SLAM + ROBOt)
# =========================================================
tmux send-keys -t $SESSION \
  "ros2 launch isabel emma.launch.py & sleep 2; ros2 launch carolina nav.launch.py use_rviz:=true" C-m

# =========================
# WAIT (importante para ROS)
# =========================
sleep 10

# =========================
# Attach
# =========================
tmux attach -t $SESSION
