#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "karto_sdk/Mapper.h"

namespace
{

struct PoseRow
{
  int index = 0;
  int state_id = 0;
  int unique_id = 0;
  double time = 0.0;
  std::string sensor;
  double odom_x = 0.0;
  double odom_y = 0.0;
  double odom_th = 0.0;
  double corr_x = 0.0;
  double corr_y = 0.0;
  double corr_th = 0.0;
  double sensor_x = 0.0;
  double sensor_y = 0.0;
  double sensor_th = 0.0;
  unsigned int beams = 0;
  double corr_step = 0.0;
  double odom_step = 0.0;
  double corr_turn = 0.0;
  double odom_turn = 0.0;
};

double normalizeAngle(double a)
{
  while (a > M_PI) {
    a -= 2.0 * M_PI;
  }
  while (a < -M_PI) {
    a += 2.0 * M_PI;
  }
  return a;
}

double dist2d(const karto::Pose2 & a, const karto::Pose2 & b)
{
  const double dx = a.GetX() - b.GetX();
  const double dy = a.GetY() - b.GetY();
  return std::sqrt(dx * dx + dy * dy);
}

std::string jsonEscape(const std::string & in)
{
  std::ostringstream out;
  for (char c : in) {
    switch (c) {
      case '\\':
        out << "\\\\";
        break;
      case '"':
        out << "\\\"";
        break;
      case '\n':
        out << "\\n";
        break;
      case '\r':
        out << "\\r";
        break;
      case '\t':
        out << "\\t";
        break;
      default:
        out << c;
    }
  }
  return out.str();
}

void writeScansCsv(const std::string & path, const std::vector<PoseRow> & rows)
{
  std::ofstream out(path);
  out << std::setprecision(17);
  out << "index,state_id,unique_id,time,sensor,odom_x,odom_y,odom_theta,"
      << "corr_x,corr_y,corr_theta,sensor_x,sensor_y,sensor_theta,beams,"
      << "corr_step,odom_step,corr_turn,odom_turn\n";
  for (const auto & r : rows) {
    out << r.index << ',' << r.state_id << ',' << r.unique_id << ',' << r.time
        << ",\"" << jsonEscape(r.sensor) << "\","
        << r.odom_x << ',' << r.odom_y << ',' << r.odom_th << ','
        << r.corr_x << ',' << r.corr_y << ',' << r.corr_th << ','
        << r.sensor_x << ',' << r.sensor_y << ',' << r.sensor_th << ','
        << r.beams << ',' << r.corr_step << ',' << r.odom_step << ','
        << r.corr_turn << ',' << r.odom_turn << '\n';
  }
}

void writeEdgesCsv(
  const std::string & path,
  const std::vector<karto::Edge<karto::LocalizedRangeScan> *> & edges)
{
  std::ofstream out(path);
  out << std::setprecision(17);
  out << "edge_index,source_state,target_state,source_unique,target_unique,state_gap,"
      << "source_x,source_y,source_theta,target_x,target_y,target_theta,"
      << "corr_distance,link_dx,link_dy,link_dtheta,"
      << "pose1_x,pose1_y,pose1_theta,pose2_x,pose2_y,pose2_theta,"
      << "cov_00,cov_01,cov_02,cov_10,cov_11,cov_12,cov_20,cov_21,cov_22\n";

  for (size_t i = 0; i < edges.size(); ++i) {
    auto * edge = edges[i];
    if (edge == nullptr || edge->GetSource() == nullptr || edge->GetTarget() == nullptr) {
      continue;
    }

    auto * source = edge->GetSource()->GetObject();
    auto * target = edge->GetTarget()->GetObject();
    if (source == nullptr || target == nullptr) {
      continue;
    }

    karto::Pose2 src_pose = source->GetCorrectedPose();
    karto::Pose2 tgt_pose = target->GetCorrectedPose();
    karto::Pose2 diff;
    karto::Pose2 pose1;
    karto::Pose2 pose2;
    karto::Matrix3 cov;

    auto * label = dynamic_cast<karto::LinkInfo *>(edge->GetLabel());
    if (label != nullptr) {
      diff = label->GetPoseDifference();
      pose1 = label->GetPose1();
      pose2 = label->GetPose2();
      cov = label->GetCovariance();
    }

    out << i << ','
        << source->GetStateId() << ',' << target->GetStateId() << ','
        << source->GetUniqueId() << ',' << target->GetUniqueId() << ','
        << std::abs(target->GetStateId() - source->GetStateId()) << ','
        << src_pose.GetX() << ',' << src_pose.GetY() << ',' << src_pose.GetHeading() << ','
        << tgt_pose.GetX() << ',' << tgt_pose.GetY() << ',' << tgt_pose.GetHeading() << ','
        << dist2d(src_pose, tgt_pose) << ','
        << diff.GetX() << ',' << diff.GetY() << ',' << diff.GetHeading() << ','
        << pose1.GetX() << ',' << pose1.GetY() << ',' << pose1.GetHeading() << ','
        << pose2.GetX() << ',' << pose2.GetY() << ',' << pose2.GetHeading();

    for (int r = 0; r < 3; ++r) {
      for (int c = 0; c < 3; ++c) {
        out << ',' << cov(r, c);
      }
    }
    out << '\n';
  }
}

void writePointsCsv(
  const std::string & path,
  const karto::LocalizedRangeScanVector & scans,
  int point_stride)
{
  if (point_stride <= 0) {
    return;
  }

  std::ofstream out(path);
  out << std::setprecision(17);
  out << "scan_index,state_id,point_index,x,y\n";
  for (size_t scan_index = 0; scan_index < scans.size(); ++scan_index) {
    auto * scan = scans[scan_index];
    if (scan == nullptr) {
      continue;
    }

    try {
      const auto & points = scan->GetPointReadings(true);
      for (size_t point_index = 0; point_index < points.size(); point_index += point_stride) {
        const auto & p = points[point_index];
        out << scan_index << ',' << scan->GetStateId() << ',' << point_index << ','
            << p.GetX() << ',' << p.GetY() << '\n';
      }
    } catch (karto::Exception & e) {
      std::cerr << "warning: failed to compute points for state "
                << scan->GetStateId() << ": " << e.GetErrorMessage() << "\n";
    }
  }
}

void writeSummaryJson(
  const std::string & path,
  const std::string & base,
  const karto::Dataset & dataset,
  const std::vector<PoseRow> & rows,
  size_t vertex_count,
  size_t edge_count)
{
  double min_x = std::numeric_limits<double>::infinity();
  double min_y = std::numeric_limits<double>::infinity();
  double max_x = -std::numeric_limits<double>::infinity();
  double max_y = -std::numeric_limits<double>::infinity();
  double corr_path = 0.0;
  double odom_path = 0.0;
  double abs_corr_turn = 0.0;
  double abs_odom_turn = 0.0;
  double max_corr_step = 0.0;
  double max_odom_step = 0.0;
  std::map<std::string, size_t> sensors;

  for (const auto & r : rows) {
    min_x = std::min(min_x, r.corr_x);
    min_y = std::min(min_y, r.corr_y);
    max_x = std::max(max_x, r.corr_x);
    max_y = std::max(max_y, r.corr_y);
    corr_path += r.corr_step;
    odom_path += r.odom_step;
    abs_corr_turn += std::abs(r.corr_turn);
    abs_odom_turn += std::abs(r.odom_turn);
    max_corr_step = std::max(max_corr_step, r.corr_step);
    max_odom_step = std::max(max_odom_step, r.odom_step);
    sensors[r.sensor]++;
  }

  std::ofstream out(path);
  out << std::setprecision(17);
  out << "{\n";
  out << "  \"base\": \"" << jsonEscape(base) << "\",\n";
  out << "  \"scans\": " << rows.size() << ",\n";
  out << "  \"dataset_lasers\": " << dataset.GetLasers().size() << ",\n";
  out << "  \"dataset_data\": " << dataset.GetData().size() << ",\n";
  out << "  \"graph_vertices\": " << vertex_count << ",\n";
  out << "  \"graph_edges\": " << edge_count << ",\n";
  out << "  \"bbox\": {\"min_x\": " << min_x << ", \"min_y\": " << min_y
      << ", \"max_x\": " << max_x << ", \"max_y\": " << max_y << "},\n";
  out << "  \"corrected_path_m\": " << corr_path << ",\n";
  out << "  \"odometric_path_m\": " << odom_path << ",\n";
  out << "  \"absolute_corrected_turn_rad\": " << abs_corr_turn << ",\n";
  out << "  \"absolute_odometric_turn_rad\": " << abs_odom_turn << ",\n";
  out << "  \"max_corrected_step_m\": " << max_corr_step << ",\n";
  out << "  \"max_odometric_step_m\": " << max_odom_step << ",\n";
  out << "  \"sensors\": {";
  bool first = true;
  for (const auto & item : sensors) {
    if (!first) {
      out << ", ";
    }
    first = false;
    out << "\"" << jsonEscape(item.first) << "\": " << item.second;
  }
  out << "}\n";
  out << "}\n";
}

}  // namespace

int main(int argc, char ** argv)
{
  if (argc < 3 || argc > 4) {
    std::cerr << "Usage: " << argv[0]
              << " <map_base_without_extension> <output_prefix> [point_stride]\n";
    return 2;
  }

  const std::string base = argv[1];
  const std::string out_prefix = argv[2];
  const int point_stride = argc == 4 ? std::max(0, std::stoi(argv[3])) : 0;

  try {
    karto::Mapper mapper;
    karto::Dataset dataset;
    std::cerr << "loading posegraph: " << base << ".posegraph\n";
    mapper.LoadFromFile(base + ".posegraph");
    std::cerr << "loading dataset: " << base << ".data\n";
    dataset.LoadFromFile(base + ".data");
    for (auto * object : dataset.GetLasers()) {
      auto * sensor = dynamic_cast<karto::Sensor *>(object);
      if (sensor != nullptr) {
        try {
          karto::SensorManager::GetInstance()->RegisterSensor(sensor, true);
        } catch (karto::Exception & e) {
          std::cerr << "warning: failed to register sensor "
                    << sensor->GetName().ToString() << ": "
                    << e.GetErrorMessage() << "\n";
        }
      }
    }
    std::cerr << "extracting scans\n";

    std::vector<PoseRow> rows;
    auto scans = mapper.GetAllProcessedScans();
    rows.reserve(scans.size());

    for (size_t i = 0; i < scans.size(); ++i) {
      auto * scan = scans[i];
      if (scan == nullptr) {
        continue;
      }

      PoseRow row;
      row.index = static_cast<int>(i);
      row.state_id = scan->GetStateId();
      row.unique_id = scan->GetUniqueId();
      row.time = scan->GetTime();
      row.sensor = scan->GetSensorName().ToString();
      const karto::Pose2 odom = scan->GetOdometricPose();
      const karto::Pose2 corr = scan->GetCorrectedPose();
      karto::Pose2 sensor;
      try {
        sensor = scan->GetSensorPose();
      } catch (karto::Exception & e) {
        std::cerr << "warning: failed to compute sensor pose for state "
                  << row.state_id << ": " << e.GetErrorMessage() << "\n";
      }
      row.odom_x = odom.GetX();
      row.odom_y = odom.GetY();
      row.odom_th = odom.GetHeading();
      row.corr_x = corr.GetX();
      row.corr_y = corr.GetY();
      row.corr_th = corr.GetHeading();
      row.sensor_x = sensor.GetX();
      row.sensor_y = sensor.GetY();
      row.sensor_th = sensor.GetHeading();
      row.beams = scan->GetNumberOfRangeReadings();

      if (!rows.empty()) {
        karto::Pose2 prev_corr(rows.back().corr_x, rows.back().corr_y, rows.back().corr_th);
        karto::Pose2 prev_odom(rows.back().odom_x, rows.back().odom_y, rows.back().odom_th);
        row.corr_step = dist2d(prev_corr, corr);
        row.odom_step = dist2d(prev_odom, odom);
        row.corr_turn = normalizeAngle(corr.GetHeading() - prev_corr.GetHeading());
        row.odom_turn = normalizeAngle(odom.GetHeading() - prev_odom.GetHeading());
      }

      rows.push_back(row);
    }

    size_t vertex_count = 0;
    size_t edge_count = 0;
    auto * graph = mapper.GetGraph();
    if (graph != nullptr) {
      std::cerr << "extracting graph\n";
      for (const auto & by_sensor : graph->GetVertices()) {
        vertex_count += by_sensor.second.size();
      }
      edge_count = graph->GetEdges().size();
      writeEdgesCsv(out_prefix + ".edges.csv", graph->GetEdges());
    }

    writeScansCsv(out_prefix + ".scans.csv", rows);
    if (point_stride > 0) {
      std::cerr << "extracting sampled points stride=" << point_stride << "\n";
      writePointsCsv(out_prefix + ".points.csv", scans, point_stride);
    }
    writeSummaryJson(out_prefix + ".summary.json", base, dataset, rows, vertex_count, edge_count);

    std::cout << "ok " << base << " scans=" << rows.size()
              << " vertices=" << vertex_count << " edges=" << edge_count << "\n";
  } catch (const boost::archive::archive_exception & e) {
    std::cerr << "archive error: " << e.what() << "\n";
    return 3;
  } catch (karto::Exception & e) {
    std::cerr << "karto error: " << e.GetErrorMessage() << "\n";
    return 5;
  } catch (const std::exception & e) {
    std::cerr << "error: " << e.what() << "\n";
    return 4;
  }

  return 0;
}
