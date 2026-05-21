# tests/test_cli.py
"""Tests for CLI module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from spark.cli import main


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


class TestCLI:
    """CLI tests."""

    def test_cli_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(main, ['--version'])
        assert result.exit_code == 0
        assert '0.2' in result.output

    def test_cli_help(self, runner):
        """Test --help flag."""
        result = runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'Spark' in result.output
        assert '--mode' in result.output
        assert '--lang' in result.output

    def test_cli_once_mode(self, runner):
        """Test --once single execution mode."""
        with patch('spark.agent.Agent') as mock_agent, \
             patch('spark.memory.MemoryManager') as mock_mem, \
             patch('spark.llm.OllamaAdapter') as mock_llm:

            mock_instance = MagicMock()
            mock_instance.run_once.return_value = "Test response"
            mock_instance.history = MagicMock()
            mock_instance.history.set_memory_manager = Mock()
            mock_instance.history.save_to_memory = Mock()
            mock_agent.return_value = mock_instance

            result = runner.invoke(main, ['--once', 'hello world'])

            assert result.exit_code == 0
            assert 'Test response' in result.output

    def test_cli_once_with_mode(self, runner):
        """Test --once with custom mode."""
        with patch('spark.agent.Agent') as mock_agent, \
             patch('spark.memory.MemoryManager') as mock_mem, \
             patch('spark.llm.OllamaAdapter') as mock_llm:

            mock_instance = MagicMock()
            mock_instance.run_once.return_value = "Test response"
            mock_instance.history = MagicMock()
            mock_agent.return_value = mock_instance

            result = runner.invoke(main, ['--once', 'test', '--mode', 'yolo'])

            assert result.exit_code == 0

    def test_cli_once_with_lang(self, runner):
        """Test --once with custom language."""
        with patch('spark.agent.Agent') as mock_agent, \
             patch('spark.memory.MemoryManager') as mock_mem, \
             patch('spark.llm.OllamaAdapter') as mock_llm:

            mock_instance = MagicMock()
            mock_instance.run_once.return_value = "Test response"
            mock_instance.history = MagicMock()
            mock_agent.return_value = mock_instance

            result = runner.invoke(main, ['--once', 'test', '--lang', 'zh'])

            assert result.exit_code == 0

    def test_cli_trust_flag(self, runner):
        """Test --trust flag."""
        with patch('spark.agent.Agent') as mock_agent, \
             patch('spark.memory.MemoryManager') as mock_mem, \
             patch('spark.llm.OllamaAdapter') as mock_llm, \
             patch('spark.cli.load_config') as mock_load:

            mock_config = MagicMock()
            mock_config.llm.model = 'test-model'
            mock_config.llm.base_url = 'http://test'
            mock_config.security.trust_current_dir = False
            mock_config.security.ask_trust_on_startup = True
            mock_load.return_value = mock_config

            mock_instance = MagicMock()
            mock_instance.run_once.return_value = "Test"
            mock_instance.history = MagicMock()
            mock_agent.return_value = mock_instance

            result = runner.invoke(main, ['--once', 'test', '--trust'])

            # Trust flag should set trust_current_dir to True
            assert mock_config.security.trust_current_dir is True

    def test_cli_model_override(self, runner):
        """Test --model flag overrides config."""
        with patch('spark.agent.Agent') as mock_agent, \
             patch('spark.memory.MemoryManager') as mock_mem, \
             patch('spark.llm.OllamaAdapter') as mock_llm, \
             patch('spark.cli.load_config') as mock_load:

            mock_config = MagicMock()
            mock_config.llm.model = 'default-model'
            mock_config.llm.base_url = 'http://default'
            mock_config.security.trust_current_dir = True
            mock_config.security.ask_trust_on_startup = False
            mock_load.return_value = mock_config

            mock_instance = MagicMock()
            mock_instance.run_once.return_value = "Test"
            mock_instance.history = MagicMock()
            mock_agent.return_value = mock_instance

            result = runner.invoke(main, ['--once', 'test', '--model', 'custom-model'])

            assert mock_config.llm.model == 'custom-model'

    def test_cli_base_url_override(self, runner):
        """Test --base-api-url flag overrides config."""
        with patch('spark.agent.Agent') as mock_agent, \
             patch('spark.memory.MemoryManager') as mock_mem, \
             patch('spark.llm.OllamaAdapter') as mock_llm, \
             patch('spark.cli.load_config') as mock_load:

            mock_config = MagicMock()
            mock_config.llm.model = 'test'
            mock_config.llm.base_url = 'http://default'
            mock_config.security.trust_current_dir = True
            mock_config.security.ask_trust_on_startup = False
            mock_load.return_value = mock_config

            mock_instance = MagicMock()
            mock_instance.run_once.return_value = "Test"
            mock_instance.history = MagicMock()
            mock_agent.return_value = mock_instance

            result = runner.invoke(main, ['--once', 'test', '--base-api-url', 'http://custom:11434'])

            assert mock_config.llm.base_url == 'http://custom:11434'

    def test_cli_memory_path(self, runner):
        """Test --memory flag sets memory path."""
        with patch('spark.agent.Agent') as mock_agent, \
             patch('spark.memory.MemoryManager') as mock_mem, \
             patch('spark.llm.OllamaAdapter') as mock_llm, \
             patch('spark.cli.load_config') as mock_load:

            mock_config = MagicMock()
            mock_config.llm.model = 'test'
            mock_config.llm.base_url = 'http://test'
            mock_config.security.trust_current_dir = True
            mock_config.security.ask_trust_on_startup = False
            mock_load.return_value = mock_config

            mock_instance = MagicMock()
            mock_instance.run_once.return_value = "Test"
            mock_instance.history = MagicMock()
            mock_agent.return_value = mock_instance

            result = runner.invoke(main, ['--once', 'test', '--memory', '/custom/memory.md'])

            assert result.exit_code == 0

    def test_cli_tui_mode(self, runner):
        """Test TUI mode (no --once flag)."""
        with patch('spark.tui.ZeroAgentApp') as mock_tui, \
             patch('spark.cli.load_config') as mock_load:

            mock_config = MagicMock()
            mock_config.security.trust_current_dir = True
            mock_config.security.ask_trust_on_startup = False
            mock_load.return_value = mock_config

            mock_app = MagicMock()
            mock_tui.return_value = mock_app

            result = runner.invoke(main, [])

            # TUI app should be created and run
            mock_app.run.assert_called_once()

    def test_cli_invalid_mode(self, runner):
        """Test invalid mode option."""
        result = runner.invoke(main, ['--mode', 'invalid'])

        assert result.exit_code != 0

    def test_cli_invalid_lang(self, runner):
        """Test invalid language option."""
        result = runner.invoke(main, ['--lang', 'invalid'])

        assert result.exit_code != 0

    def test_cli_config_file(self, runner):
        """Test --config flag."""
        with patch('spark.agent.Agent') as mock_agent, \
             patch('spark.memory.MemoryManager') as mock_mem, \
             patch('spark.llm.OllamaAdapter') as mock_llm, \
             patch('spark.cli.load_config') as mock_load:

            mock_config = MagicMock()
            mock_config.llm.model = 'test'
            mock_config.llm.base_url = 'http://test'
            mock_config.security.trust_current_dir = True
            mock_config.security.ask_trust_on_startup = False
            mock_load.return_value = mock_config

            mock_instance = MagicMock()
            mock_instance.run_once.return_value = "Test"
            mock_instance.history = MagicMock()
            mock_agent.return_value = mock_instance

            result = runner.invoke(main, ['--once', 'test', '--config', '/path/to/config.yaml'])

            mock_load.assert_called()