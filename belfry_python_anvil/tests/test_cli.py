# pylint: disable=redefined-outer-name,unused-variable,expression-not-assigned

import json
import pytest
from click.testing import CliRunner
from unittest import mock

from belfry_python_anvil.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def set_key(monkeypatch):
    monkeypatch.setenv("ANVIL_API_KEY", "MY_KEY")


def describe_cli():
    @mock.patch("belfry_python_anvil.api.Anvil.get_current_user")
    def it_handles_no_key(anvil, runner):
        res = runner.invoke(cli, ["current-user"])
        assert anvil.call_count == 0
        assert isinstance(res.exception, ValueError)

    @mock.patch("belfry_python_anvil.api.Anvil.get_current_user")
    def it_handles_key(anvil, runner, monkeypatch):
        set_key(monkeypatch)
        res = runner.invoke(cli, ["current-user"])
        assert anvil.call_count == 1
        assert not isinstance(res.exception, ValueError)

    def describe_current_user():
        @mock.patch("belfry_python_anvil.api.Anvil.query")
        def it_queries(query, runner, monkeypatch):
            set_key(monkeypatch)
            query.return_value = {"currentUser": {"name": "Cameron"}}

            res = runner.invoke(cli, ['current-user'])
            assert "{'name': 'Cameron'}" in res.output
            assert "User data:" in res.output
            assert query.call_count == 1

        @mock.patch("belfry_python_anvil.api.Anvil.query")
        def it_handles_headers(query, runner, monkeypatch):
            set_key(monkeypatch)
            query.return_value = {
                "response": {"currentUser": {"name": "Cameron"}},
                "headers": {"Header-1": "val1", "Header-2": "val2"},
            }

            res = runner.invoke(cli, ['--debug', 'current-user'])
            assert "{'name': 'Cameron'}" in res.output
            assert "User data:" in res.output
            assert "{'Header-1': 'val1'," in res.output
            assert query.call_count == 1

    def describe_generate_pdf():
        @mock.patch("belfry_python_anvil.api.Anvil.generate_pdf")
        def it_handles_files(generate_pdf, runner, monkeypatch):
            set_key(monkeypatch)

            in_data = json.dumps({"data": "", "title": "My Title"})
            generate_pdf.return_value = "Some bytes"
            mock_open = mock.mock_open(read_data=in_data)

            with mock.patch("click.open_file", mock_open) as m:
                res = runner.invoke(
                    cli, ['generate-pdf', '-i', 'infile', '-o', 'outfile']
                )
                generate_pdf.assert_called_once_with(in_data, debug=False)
                m().write.assert_called_once_with("Some bytes")

    def describe_gql_query():
        @mock.patch("belfry_python_anvil.api.Anvil.query")
        def it_works_query_only(query, runner, monkeypatch):
            set_key(monkeypatch)

            query.return_value = dict(
                eid="abc123",
                name="Some User",
            )

            query_str = """
            query SomeQuery {
                someQuery { eid name }
            }
            """

            runner.invoke(cli, ['gql-query', '-q', query_str])
            query.assert_called_once_with(query_str, variables=None, debug=False)

        @mock.patch("belfry_python_anvil.api.Anvil.query")
        def it_works_query_and_variables(query, runner, monkeypatch):
            set_key(monkeypatch)

            query.return_value = dict(
                eid="abc123",
                name="Some User",
            )

            query_str = """
            query SomeQuery ($eid: String) {
                someQuery(eid: $eid) { eid name }
            }
            """

            variables = json.dumps(dict(eid="abc123"))

            runner.invoke(cli, ['gql-query', '-q', query_str, '-v', variables])
            query.assert_called_once_with(query_str, variables=variables, debug=False)
