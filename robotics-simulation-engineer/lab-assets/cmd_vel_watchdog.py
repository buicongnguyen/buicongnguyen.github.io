"""Forward fresh Twist commands and publish zero when input becomes stale."""

import argparse
import time

import rclpy
from geometry_msgs.msg import Twist
from lab_contracts import is_stale
from rclpy.clock import Clock, ClockType
from rclpy.node import Node


class TwistWatchdog(Node):
    def __init__(self, input_topic: str, output_topic: str, timeout: float, rate: float):
        super().__init__("cmd_vel_watchdog")
        self.timeout = timeout
        self.last_receipt = None
        self.latest = Twist()
        self.stale = True
        self.publisher = self.create_publisher(Twist, output_topic, 10)
        self.subscription = self.create_subscription(Twist, input_topic, self.on_command, 10)
        # The safety timeout must keep running even if a caller later enables
        # use_sim_time and the Isaac Sim timeline is paused.
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(1.0 / rate, self.on_timer, clock=self.steady_clock)
        self.get_logger().info(
            f"Forwarding {input_topic} -> {output_topic}; timeout={timeout:.3f}s; rate={rate:.1f}Hz"
        )

    def on_command(self, message: Twist) -> None:
        self.latest = message
        self.last_receipt = time.monotonic()
        if self.stale:
            self.get_logger().info("Command stream is fresh")
        self.stale = False

    def on_timer(self) -> None:
        now = time.monotonic()
        age = None if self.last_receipt is None else now - self.last_receipt
        now_stale = is_stale(self.last_receipt, now, self.timeout)
        if now_stale:
            self.publisher.publish(Twist())
            if not self.stale:
                self.get_logger().warn(f"Command stale at {age:.3f}s; publishing zero Twist")
        else:
            self.publisher.publish(self.latest)
        self.stale = now_stale


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/cmd_vel_raw")
    parser.add_argument("--output", default="/cmd_vel")
    parser.add_argument("--timeout", type=float, default=0.5)
    parser.add_argument("--rate", type=float, default=20.0)
    args = parser.parse_args()
    if args.timeout <= 0.0 or args.rate <= 0.0:
        parser.error("--timeout and --rate must be positive")

    rclpy.init()
    node = TwistWatchdog(args.input, args.output, args.timeout, args.rate)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publisher.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
