// Copyright (c) 2026 Paul N. Beuchat. MIT License.
// Bounded integration observer. It opens no camera and issues no commands.
#include <rgbd_object_detector/overlay.hpp>
#include <rgbd_camera_interfaces/msg/status.hpp>
#include <rgbd_object_detector_interfaces/msg/status.hpp>
#include <rclcpp/rclcpp.hpp>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>

using Frame = rgbd_camera_interfaces::msg::Frame;
using Batch = rgbd_object_detector_interfaces::msg::Batch;
using Overlay = rgbd_object_detector_interfaces::msg::OverlayFrame;
using CameraStatus = rgbd_camera_interfaces::msg::Status;
using DetectorStatus = rgbd_object_detector_interfaces::msg::Status;
int64_t now_ns() { return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

void ppm(const std::string& path, const sensor_msgs::msg::Image& image) {
  std::ofstream file(path, std::ios::binary);
  file << "P6\n" << image.width << ' ' << image.height << "\n255\n";
  for (uint32_t y = 0; y < image.height; ++y) for (uint32_t x = 0; x < image.width; ++x) {
    const auto p = y*image.step + x*3;
    const char rgb[3]{char(image.data[p+2]), char(image.data[p+1]), char(image.data[p])};
    file.write(rgb, 3);
  }
}

class Probe : public rclcpp::Node {
 public:
  Probe() : Node("integration_probe") {
    directory_ = declare_parameter<std::string>("output", "/tmp/rgbd-integration-probe");
    const auto prefix = declare_parameter<std::string>("source_namespace", "/perception");
    limit_ = declare_parameter<int>("exact_samples", 25);
    marker_ = declare_parameter<bool>("marker", true);
    if (limit_ < 0 || limit_ > 100 || std::filesystem::exists(directory_)) throw std::runtime_error("Use a new output and 0..100 exact samples");
    std::filesystem::create_directories(directory_);
    batches_.open(directory_ + "/batches.csv"); camera_.open(directory_ + "/camera.csv"); detector_.open(directory_ + "/detector.csv");
    exact_.open(directory_ + "/exact.csv");
    exact_ << "source_id,generation,sequence,acquisition_ns,model_id,model_profile_sha256\n";
    if (!batches_ || !camera_ || !detector_) throw std::runtime_error("Cannot open observer files");
    batches_ << "arrival_ns,sequence,acquisition_ns,unix_offset_ns,completed_ns,source_age_ns,preprocess_ns,inference_ns,postprocess_ns,detections,valid,invalid,truncated,nms_count,generation,model_id,model_profile_sha256,labels\n";
    camera_ << "arrival_ns,observed_ns,state,frames,pairs,rejected,gaps,last_acquisition_ns,last_skew_ns,source_id,generation,detail\n";
    detector_ << "arrival_ns,observed_ns,state,received,processed,replaced,rejected,stale,superseded,failures,pending,overlay_state,overlay_rendered,overlay_replaced,overlay_stale,overlay_no_consumers,overlay_failures,overlay_last_render_ns\n";
    const auto qos = rclcpp::SensorDataQoS().keep_last(1);
    batch_sub_ = create_subscription<Batch>(prefix + "/detector/batches", qos, [this](Batch::ConstSharedPtr b) {
      size_t valid = 0; std::string labels;
      for (const auto& s : b->spatial) valid += s.valid;
      for (const auto& d : b->detections.detections) if (!d.results.empty()) labels += d.results[0].hypothesis.class_id + ";";
      batches_ << now_ns() << ',' << b->capture.sequence << ',' << b->capture.acquisition_ns << ',' << b->capture.unix_offset_ns << ',' << b->completed_ns << ','
        << b->source_age_ns << ',' << b->preprocess_ns << ',' << b->inference_ns << ',' << b->postprocess_ns << ','
        << b->detections.detections.size() << ',' << valid << ',' << b->spatial.size()-valid << ',' << b->truncated << ',' << b->nms_count << ','
        << b->capture.generation << ',' << b->model_id << ',' << b->model_profile_sha256 << ',' << std::quoted(labels) << '\n';
    });
    camera_sub_ = create_subscription<CameraStatus>(prefix + "/camera/status", qos, [this](CameraStatus::ConstSharedPtr s) {
      camera_ << now_ns() << ',' << s->observed_ns << ',' << s->state << ',' << s->frames << ',' << s->pairs_received << ','
        << s->rejected_pairs << ',' << s->sequence_gaps << ',' << s->last_acquisition_ns << ',' << s->last_skew_ns << ','
        << s->source_id << ',' << s->generation << ',' << std::quoted(s->detail, '"', '"') << '\n';
    });
    detector_sub_ = create_subscription<DetectorStatus>(prefix + "/detector/status", qos, [this](DetectorStatus::ConstSharedPtr s) {
      detector_ << now_ns() << ',' << s->observed_ns << ',' << s->state << ',' << s->received << ',' << s->processed << ','
        << s->replaced << ',' << s->rejected << ',' << s->stale << ',' << s->superseded << ',' << s->failures << ',' << s->pending << ','
        << s->overlay_state << ',' << s->overlay_rendered << ',' << s->overlay_replaced << ',' << s->overlay_stale << ','
        << s->overlay_no_consumers << ',' << s->overlay_failures << ',' << s->overlay_last_render_ns << '\n';
    });
    if (limit_) {
      frame_sub_ = create_subscription<Frame>(prefix + "/camera/frames", qos, [this](Frame::ConstSharedPtr f) {
        const auto key = std::make_pair(f->capture.generation, f->capture.sequence);
        originals_[key] = f;
        while (originals_.size() > 12) originals_.erase(originals_.begin());
        match();
      });
      overlay_sub_ = create_subscription<Overlay>(prefix + "/detector/overlay/frame", qos, [this](Overlay::ConstSharedPtr f) {
        overlays_[{f->batch.capture.generation, f->batch.capture.sequence}] = f;
        while (overlays_.size() > 12) overlays_.erase(overlays_.begin());
        match();
      });
    }
    timer_ = create_wall_timer(std::chrono::seconds(1), [this] {
      batches_.flush(); camera_.flush(); detector_.flush(); exact_.flush();
      if (limit_ && checked_ >= limit_) {
        frame_sub_.reset(); overlay_sub_.reset(); originals_.clear(); overlays_.clear();
      }
      std::ofstream(directory_ + "/exact.txt") << checked_ << '\n';
    });
  }
 private:
  void match() {
    for (auto it = overlays_.begin(); it != overlays_.end() && checked_ < limit_;) {
      const auto found = originals_.find(it->first);
      if (found == originals_.end()) { ++it; continue; }
      const auto& frame = *found->second; const auto& output = *it->second;
      if (frame.capture != output.batch.capture || frame.calibration_id != output.batch.calibration_id)
        throw std::runtime_error("Exact overlay capture association failed");
      const auto expected = rgbd_object_detector::render_overlay(frame.rgb, output.batch, true, marker_);
      if (*expected != output.image) throw std::runtime_error("Overlay pixels differ from the exact original acquisition");
      exact_ << frame.capture.source_id << ',' << frame.capture.generation << ',' << frame.capture.sequence << ','
        << frame.capture.acquisition_ns << ',' << output.batch.model_id << ',' << output.batch.model_profile_sha256 << '\n';
      if (!checked_) { ppm(directory_ + "/source.ppm", frame.rgb); ppm(directory_ + "/overlay.ppm", output.image); }
      ++checked_; originals_.erase(found); it = overlays_.erase(it);
    }
  }
  std::string directory_; int limit_ = 0, checked_ = 0; bool marker_ = false;
  std::ofstream batches_, camera_, detector_, exact_;
  std::map<std::pair<std::string, uint64_t>, Frame::ConstSharedPtr> originals_;
  std::map<std::pair<std::string, uint64_t>, Overlay::ConstSharedPtr> overlays_;
  rclcpp::Subscription<Batch>::SharedPtr batch_sub_;
  rclcpp::Subscription<CameraStatus>::SharedPtr camera_sub_;
  rclcpp::Subscription<DetectorStatus>::SharedPtr detector_sub_;
  rclcpp::Subscription<Frame>::SharedPtr frame_sub_;
  rclcpp::Subscription<Overlay>::SharedPtr overlay_sub_;
  rclcpp::TimerBase::SharedPtr timer_;
};
int main(int argc, char** argv) {
  rclcpp::init(argc, argv);
  try { rclcpp::spin(std::make_shared<Probe>()); rclcpp::shutdown(); return 0; }
  catch (const std::exception& error) { std::cerr << error.what() << '\n'; rclcpp::shutdown(); return 1; }
}
