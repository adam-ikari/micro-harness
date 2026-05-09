# tests/test_security.py
import pytest
from micro_harness.security import SecurityManager, Decision
from micro_harness.security.permission import PermissionManager
from micro_harness.security.risk_detector import RiskDetector
from micro_harness.config import SecurityConfig


def test_permission_allow():
    """测试权限允许"""
    config = SecurityConfig(permissions={"run_shell": "allow"})
    pm = PermissionManager(config)

    decision = pm.check("run_shell", {"command": "ls"})
    assert decision == Decision.ALLOW


def test_permission_deny():
    """测试权限拒绝"""
    config = SecurityConfig(permissions={"run_shell": "deny"})
    pm = PermissionManager(config)

    decision = pm.check("run_shell", {"command": "ls"})
    assert decision == Decision.DENY


def test_permission_confirm():
    """测试需要确认"""
    config = SecurityConfig(permissions={"run_shell": "confirm"})
    pm = PermissionManager(config)

    decision = pm.check("run_shell", {"command": "ls"})
    assert decision == Decision.CONFIRM


def test_risk_detector_blocked():
    """测试禁止命令检测"""
    config = SecurityConfig(
        blocked_commands=["rm -rf /", "mkfs"]
    )
    rd = RiskDetector(config)

    assert rd.is_blocked("rm -rf /") is True
    assert rd.is_blocked("mkfs /dev/sda1") is True
    assert rd.is_blocked("ls -la") is False


def test_risk_detector_needs_confirm():
    """测试高风险命令检测"""
    config = SecurityConfig(
        confirm_patterns=["rm", "sudo", "git push"]
    )
    rd = RiskDetector(config)

    assert rd.needs_confirm("rm file.txt") is True
    assert rd.needs_confirm("sudo apt install") is True
    assert rd.needs_confirm("git push origin main") is True
    assert rd.needs_confirm("ls -la") is False


def test_security_manager_normal_mode():
    """测试正常模式"""
    config = SecurityConfig(
        permissions={"run_shell": "allow"},
        blocked_commands=["rm -rf /"],
        confirm_patterns=["rm"],
    )
    sm = SecurityManager(config, yolo=False)

    # 禁止命令应该被拒绝
    assert sm.check("run_shell", {"command": "rm -rf /"}) == Decision.DENY

    # 高风险命令需要确认（即使权限是 allow）
    assert sm.check("run_shell", {"command": "rm file.txt"}) == Decision.CONFIRM

    # 普通命令允许
    assert sm.check("run_shell", {"command": "ls -la"}) == Decision.ALLOW


def test_security_manager_yolo_mode():
    """测试 YOLO 模式"""
    config = SecurityConfig(
        permissions={"run_shell": "confirm"},
        blocked_commands=["rm -rf /"],
        confirm_patterns=["rm"],
    )
    sm = SecurityManager(config, yolo=True)

    # 禁止命令仍然被拒绝
    assert sm.check("run_shell", {"command": "rm -rf /"}) == Decision.DENY

    # 高风险命令需要确认
    assert sm.check("run_shell", {"command": "rm file.txt"}) == Decision.CONFIRM

    # 普通命令自动允许（跳过权限检查）
    assert sm.check("run_shell", {"command": "ls -la"}) == Decision.ALLOW
