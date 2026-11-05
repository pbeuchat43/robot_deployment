// Copyright (c) 2026 Paul N. Beuchat. MIT License.
// Read-only observer: compare both independently received results and exact pixels.
#include <rgbd_object_detector/overlay.hpp>
#include <rgbd_object_detector_interfaces/msg/combined_overlay_frame.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/serialization.hpp>
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>

using Frame = rgbd_camera_interfaces::msg::Frame;
using CaptureDetections = rgbd_object_detector_interfaces::msg::CaptureDetections;
using Overlay = rgbd_object_detector_interfaces::msg::CombinedOverlayFrame;
using Key = std::pair<std::string, uint64_t>;
class CombinedProbe : public rclcpp::Node {
 public:
  CombinedProbe() : Node("combined_integration_probe") {
    directory_ = declare_parameter<std::string>("output", "/tmp/rgbd-combined-probe");
    const auto prefix = declare_parameter<std::string>("source_namespace", "/perception");
    limit_ = declare_parameter<int>("exact_samples", 25);
    marker_ = declare_parameter<bool>("marker", false);
    if (limit_ < 1 || limit_ > 100 || std::filesystem::exists(directory_)) throw std::runtime_error("Use a new output and 1..100 samples");
    std::filesystem::create_directories(directory_);
    exact_.open(directory_ + "/exact.csv");
    if (!exact_) throw std::runtime_error("Cannot open observer file");
    exact_ << "generation,sequence,acquisition_ns,first_model,second_model,first_detections,second_detections,render_ns\n";
    const auto qos = rclcpp::SensorDataQoS().keep_last(1);
    frame_ = create_subscription<Frame>(prefix + "/camera/frames", qos, [this](Frame::ConstSharedPtr f) {
      frames_[{f->capture.generation, f->capture.sequence}] = f; trim(frames_); match();
    });
    for (size_t i = 0; i < 2; ++i)
      capture_detections_subscriptions_[i] = create_subscription<CaptureDetections>(prefix + (i == 0 ? "/detector_cones/capture_detections" : "/detector_coco/capture_detections"), qos,
          [this, i](CaptureDetections::ConstSharedPtr b) { capture_detections_[i][{b->capture.generation, b->capture.sequence}] = b; trim(capture_detections_[i]); match(); });
    overlay_ = create_subscription<Overlay>(prefix + "/combined_overlay/overlay/frame", qos, [this](Overlay::ConstSharedPtr o) {
      overlays_[{o->capture_detections[0].capture.generation, o->capture_detections[0].capture.sequence}] = o; trim(overlays_); match();
    });
    timer_ = create_wall_timer(std::chrono::seconds(1), [this] {
      exact_.flush(); std::ofstream(directory_ + "/exact.txt") << checked_ << '\n';
      if (checked_ >= limit_) {
        frame_.reset(); overlay_.reset(); capture_detections_subscriptions_ = {}; frames_.clear(); overlays_.clear(); capture_detections_ = {};
      }
    });
  }
 private:
  template<class T> void trim(T& cache) { while (cache.size() > 12) cache.erase(cache.begin()); }
  void match() {
    for (auto it = overlays_.begin(); it != overlays_.end() && checked_ < limit_;) {
      const auto f = frames_.find(it->first);
      const auto a = capture_detections_[0].find(it->first), b = capture_detections_[1].find(it->first);
      if (f == frames_.end() || a == capture_detections_[0].end() || b == capture_detections_[1].end()) { ++it; continue; }
      const auto& frame = *f->second; const auto& output = *it->second;
      // Hypothesis poses contain NaNs, so generated operator== is unsuitable.
      // Compare the actual ROS serialized bytes of each unmodified result instead.
      rclcpp::Serialization<CaptureDetections> serialization;
      for (size_t i = 0; i < 2; ++i) {
        rclcpp::SerializedMessage received(256*1024), retained(256*1024);
        // Initialize alignment padding as well as serialized fields.
        for (auto* message : {&received, &retained}) {
          auto& buffer = message->get_rcl_serialized_message();
          std::fill(buffer.buffer, buffer.buffer + buffer.buffer_capacity, 0);
        }
        serialization.serialize_message((i == 0 ? a : b)->second.get(), &received);
        serialization.serialize_message(&output.capture_detections[i], &retained);
        const auto& x = received.get_rcl_serialized_message(); const auto& y = retained.get_rcl_serialized_message();
        if (x.buffer_length != y.buffer_length || !std::equal(x.buffer, x.buffer + x.buffer_length, y.buffer) ||
            frame.capture != output.capture_detections[i].capture || frame.calibration_id != output.capture_detections[i].calibration_id)
          throw std::runtime_error("Combined result differs from independent result or original capture");
      }
      const auto expected = rgbd_object_detector::render_combined_overlay(frame.rgb, output.capture_detections[0], output.capture_detections[1], true, marker_);
      if (*expected != output.image) throw std::runtime_error("Combined pixels differ from the exact source and both model results");
      exact_ << frame.capture.generation << ',' << frame.capture.sequence << ',' << frame.capture.acquisition_ns << ','
          << output.capture_detections[0].model_id << ',' << output.capture_detections[1].model_id << ','
          << output.capture_detections[0].detections.detections.size() << ',' << output.capture_detections[1].detections.detections.size() << ','
          << output.render_completed_ns - output.render_started_ns << '\n';
      ++checked_; frames_.erase(f); capture_detections_[0].erase(a); capture_detections_[1].erase(b); it = overlays_.erase(it);
    }
  }
  std::string directory_; int limit_ = 25, checked_ = 0; bool marker_ = false;
  std::ofstream exact_;
  std::map<Key, Frame::ConstSharedPtr> frames_;
  std::array<std::map<Key, CaptureDetections::ConstSharedPtr>, 2> capture_detections_;
  std::map<Key, Overlay::ConstSharedPtr> overlays_;
  rclcpp::Subscription<Frame>::SharedPtr frame_;
  std::array<rclcpp::Subscription<CaptureDetections>::SharedPtr, 2> capture_detections_subscriptions_;
  rclcpp::Subscription<Overlay>::SharedPtr overlay_;
  rclcpp::TimerBase::SharedPtr timer_;
};
int main(int argc, char** argv) {
  rclcpp::init(argc, argv);
  try { rclcpp::spin(std::make_shared<CombinedProbe>()); rclcpp::shutdown(); return 0; }
  catch (const std::exception& error) { std::cerr << error.what() << '\n'; rclcpp::shutdown(); return 1; }
}
