"""Forward fresh Twist commands and publish zero when input becomes stale."""

import argparse
import math
import time

import rclpy
from geometry_msgs.msg import Twist
from lab_contracts import is_stale
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions


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
    # argparse accepts "nan" and "inf"; a NaN timeout would never go stale (fail open).
    if not (math.isfinite(args.timeout) and math.isfinite(args.rate)) or args.timeout <= 0.0 or args.rate <= 0.0:
        parser.error("--timeout and --rate must be positive and finite")

    # rclpy's default SIGINT handler shuts the context down before spin returns, which
    # makes the final zero command impossible. Leave SIGINT to Python instead: Ctrl-C
    # raises KeyboardInterrupt while the context is still valid.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = TwistWatchdog(args.input, args.output, args.timeout, args.rate)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # An external shutdown can still invalidate the context first, so the final
        # zero command stays best effort and must not mask the exit path.
        if rclpy.ok():
            try:
                node.publisher.publish(Twist())
            except Exception as error:
                node.get_logger().error(f"Final zero Twist was not published: {error}")
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
