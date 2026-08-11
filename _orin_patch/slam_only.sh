#!/bin/bash
# este es el slam + teleop pero sin las camaras
SESSION=slam-

# =========================
# ROS2 Humble
# =========================
source /opt/ros/humble/setup.bash
source ~/Documents/orbbec_ws/install/setup.bash
source ~/emma/install/setup.bash

# =========================
# ALWAYS START CLEAN
# =========================
timeout 1 ros2 topic pub --once /controller/cmd_vel geometry_msgs/msg/Twist "{}" >/tmp/c8_stop_cmd.log 2>&1 || true
timeout 1 ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}" >>/tmp/c8_stop_cmd.log 2>&1 || true

tmux has-session -t $SESSION 2>/dev/null && {
  echo "Killing previous tmux session: $SESSION"
  tmux kill-session -t $SESSION
}

for pattern in \
  "[r]os2 launch slam carolina.launch.py" \
  "[r]os_robot_controller" \
  "[o]dom_publisher" \
  "[e]kf_node" \
  "[s]ervo_controller" \
  "[s]llidar_node" \
  "[s]ync_slam_toolbox_node"
do
  pkill -TERM -f "$pattern" 2>/dev/null || true
done
sleep 2
for pattern in \
  "[r]os2 launch slam carolina.launch.py" \
  "[r]os_robot_controller" \
  "[o]dom_publisher" \
  "[e]kf_node" \
  "[s]ervo_controller" \
  "[s]llidar_node" \
  "[s]ync_slam_toolbox_node"
do
  pkill -KILL -f "$pattern" 2>/dev/null || true
done

if [ ! -e /dev/lidar ]; then
  echo "ERROR: /dev/lidar no existe. Revisa ch34x/udev antes de iniciar SLAM."
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
  "ros2 launch slam carolina.launch.py robot_name:=/ slam_algorithm:=slam_toolbox use_rviz:=false" C-m

# =========================
# WAIT (importante para ROS)
# =========================
sleep 10

# =========================================================
# Pane 2 → teleop
# =========================================================
tmux split-window -v
tmux send-keys -t $SESSION:. \
  "ros2 run isabel nav_teleop" C-m
# =========================
# Layout bonito
# =========================
tmux select-layout tiled

# =========================
# Attach
# =========================
tmux attach -t $SESSION
