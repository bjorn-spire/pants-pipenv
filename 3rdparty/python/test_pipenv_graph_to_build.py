import json
import textwrap
from pathlib import Path
from typing import List, Optional

from attr import Factory, asdict, attrib, attrs
from py import path

from .pipenv_graph_to_build import (
    Dependency,
    create_build_file,
    main,
    read_dependencies,
    read_direct_dependencies,
)


@attrs
class Package:
    key: str = attrib()
    package_name: str = attrib()
    installed_version: str = attrib()


@attrs
class DependencyFactory:
    package: Package = attrib()
    dependencies: List["DependencyFactory"] = attrib(default=Factory(list))


def _dependency(
    key: str, version: str, dependencies: Optional[List[Package]] = None, package_name: Optional[str] = None
) -> DependencyFactory:
    package_name = package_name or key
    dependencies = dependencies or []

    return DependencyFactory(package=_package(key, version, package_name), dependencies=dependencies)


def _package(key, version, package_name: Optional[str] = None) -> Package:
    return Package(key, package_name or key, version)


class TestReadDependencies:
    def _read(self, input_dependencies) -> List[Dependency]:
        return list(read_dependencies(json.dumps(list(map(asdict, input_dependencies)))))

    def test_extracts_all_top_level_dependencies(self) -> None:
        input_dependencies = [_dependency("virtualenv", "16.4.3"), _dependency("adsb", "0.1.1")]

        returned_dependencies = self._read(input_dependencies)

        assert returned_dependencies == [
            Dependency("adsb", "adsb", "0.1.1"),
            Dependency("virtualenv", "virtualenv", "16.4.3"),
        ]

    def test_parses_direct_dependencies(self) -> None:
        input_dependencies = [
            _dependency(
                "first-dependency",
                "1.0.0",
                package_name="first_dependency",
                dependencies=[_package("subdependency", "0.9.0")],
            ),
            _dependency("subdependency", "0.9.0"),
        ]

        returned_dependencies = self._read(input_dependencies)

        assert returned_dependencies == [
            Dependency(
                "first-dependency",
                "first_dependency",
                "1.0.0",
                dependencies=[Dependency("subdependency", "subdependency", "0.9.0")],
            ),
            Dependency("subdependency", "subdependency", "0.9.0"),
        ]

    def test_parses_any_level_deep_dependencies(self) -> None:
        input_dependencies = [
            _dependency(
                "top-dependency",
                "2.0.0",
                package_name="top_dependency",
                dependencies=[_package("subdependency", "subdependency", "0.1.0")],
            ),
            _dependency(
                "subdependency",
                "0.1.0",
                [_package("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            _dependency("second-level-dependency", "0.2.0"),
        ]
        returned_dependencies = self._read(input_dependencies)

        assert returned_dependencies == [
            Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
            Dependency(
                "subdependency",
                "subdependency",
                "0.1.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            Dependency(
                "top-dependency",
                "top_dependency",
                "2.0.0",
                dependencies=[
                    Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
                    Dependency("subdependency", "subdependency", "0.1.0"),
                ],
            ),
        ]

    def test_deduplicates_dependencies_in_list(self) -> None:
        input_dependencies = [
            _dependency(
                "top-dependency",
                "2.0.0",
                package_name="top_dependency",
                dependencies=[
                    _package("subdependency", "0.1.0"),
                    _package("subdependency-with-same-second-level", "0.2.0"),
                ],
            ),
            _dependency("subdependency", "0.1.0", [_package("second-level-dependency", "0.2.0")]),
            _dependency(
                "subdependency-with-same-second-level",
                "0.2.0",
                [_package("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            _dependency("second-level-dependency", "0.2.0"),
        ]

        returned_dependencies = self._read(input_dependencies)

        assert returned_dependencies == [
            Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
            Dependency(
                "subdependency",
                "subdependency",
                "0.1.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            Dependency(
                "subdependency-with-same-second-level",
                "subdependency-with-same-second-level",
                "0.2.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            Dependency(
                "top-dependency",
                "top_dependency",
                "2.0.0",
                dependencies=[
                    Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
                    Dependency("subdependency", "subdependency", "0.1.0"),
                    Dependency(
                        "subdependency-with-same-second-level",
                        "subdependency-with-same-second-level",
                        "0.2.0",
                    ),
                ],
            ),
        ]

    def test_sort_dependencies_in_alphabetical_order(self) -> None:
        """It kind of feels like this isn't required after writing it
        since it's also enforced in all other tests
        """
        input_dependencies = [
            _dependency(
                "top-dependency",
                "2.0.0",
                package_name="top_dependency",
                dependencies=[
                    _package("subdependency", "0.1.0"),
                    _package("subdependency-with-same-second-level", "0.2.0"),
                ],
            ),
            _dependency("subdependency", "0.1.0", [_package("second-level-dependency", "0.2.0")]),
            _dependency(
                "subdependency-with-same-second-level",
                "0.2.0",
                [_package("second-level-dependency", "0.2.0")],
            ),
            _dependency("second-level-dependency", "0.2.0"),
            _dependency("attrs", "18.1.0"),
        ]

        returned_dependencies = self._read(input_dependencies)

        assert returned_dependencies == [
            Dependency("attrs", "attrs", "18.1.0"),
            Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
            Dependency(
                "subdependency",
                "subdependency",
                "0.1.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            Dependency(
                "subdependency-with-same-second-level",
                "subdependency-with-same-second-level",
                "0.2.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            Dependency(
                "top-dependency",
                "top_dependency",
                "2.0.0",
                dependencies=[
                    Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
                    Dependency("subdependency", "subdependency", "0.1.0"),
                    Dependency(
                        "subdependency-with-same-second-level",
                        "subdependency-with-same-second-level",
                        "0.2.0",
                    ),
                ],
            ),
        ]

    def test_extracts_dependencies_that_are_only_available_as_subdependencies(self) -> None:
        """This is a case that I so far have only seen with setuptools"""
        input_dependencies = [
            _dependency(
                "top-dependency",
                "2.0.0",
                package_name="top_dependency",
                dependencies=[_package("setuptools", "0.1.0")],
            )
        ]

        returned_dependencies = self._read(input_dependencies)

        assert returned_dependencies == [
            Dependency("setuptools", "setuptools", "0.1.0"),
            Dependency(
                "top-dependency",
                "top_dependency",
                "2.0.0",
                dependencies=[Dependency("setuptools", "setuptools", "0.1.0")],
            ),
        ]

    def test_make_lookups_on_case_normalized_keys(self) -> None:
        input_dependencies = [
            _dependency(
                "top-dependency",
                "2.0.0",
                package_name="top_dependency",
                dependencies=[_package("SubDependency", "0.1.0", package_name="subDEPENDENCY")],
            ),
            _dependency("sUbdependency", "0.1.0", package_name="SUBdependency"),
        ]

        returned_dependencies = self._read(input_dependencies)

        assert returned_dependencies == [
            Dependency("subdependency", "subdependency", "0.1.0"),
            Dependency(
                "top-dependency",
                "top_dependency",
                "2.0.0",
                dependencies=[Dependency("subdependency", "subdependency", "0.1.0")],
            ),
        ]


class TestReadDirectDependenciesFromPipfile:
    def test_parses_out_all_packages(self) -> None:
        pipfile = (
            # language=toml
            """
            [[source]]
            name = "pypi"
            url = "https://pypi.org/simple"
            verify_ssl = true
            
            [dev-packages]
            
            [packages]
            requests = "*"
            """
        )

        direct_dependencies = read_direct_dependencies(pipfile)

        assert direct_dependencies == ["requests"]

    def test_parses_out_all_packages_and_dev_packages(self) -> None:
        pipfile = (
            # language=toml
            """
            [[source]]
            name = "pypi"
            url = "https://pypi.org/simple"
            verify_ssl = true
            
            [dev-packages]
            pytest = "*"
            
            [packages]
            attrs = "*"
            """
        )

        direct_dependencies = read_direct_dependencies(pipfile)

        assert direct_dependencies == ["attrs", "pytest"]

    def test_can_read_toml_proper_with_arrayed_items(self) -> None:
        """The [[source]] syntax indicates that the section is part
        of an array. I tried implementing with ConfigParser at first
        but that didn't work out at all. So use TOML now
        """
        pipfile = (
            # language=toml
            """
            [[source]]
            name = "pypi"
            url = "https://pypi.org/simple"
            verify_ssl = true
            
            [[source]]
            name = "secondary"
            url = "https://nirror.archive.org/simple"
            verify_ssl = true
            
            [dev-packages]
            
            [packages]
            """
        )

        direct_dependencies = read_direct_dependencies(pipfile)

        assert direct_dependencies == [], "didn't expect any dependencies"

    def test_normalizes_the_case_of_packages_to_lower(self) -> None:
        pipfile = (
            # language=toml
            """
            [[source]]
            name = "pypi"
            url = "https://pypi.org/simple"
            verify_ssl = true
            
            [dev-packages]
            
            [packages]
            PyMySQL = "*"
            """
        )

        direct_dependencies = read_direct_dependencies(pipfile)

        assert direct_dependencies == ["pymysql"]


class TestCreateBuildFile:
    def test_creates_a_build_file_containing_direct_dependencies(self) -> None:
        direct_dependencies = ["only-dependency"]
        all_dependencies = [
            Dependency("only-dependency", "only-dependency", "1.0.0"),
            Dependency("superfluous", "superfluous", "0.0.1"),
        ]

        build_string = create_build_file(all_dependencies, direct_dependencies)

        assert build_string == textwrap.dedent(
            # language=python
            """
            python_requirement_library(
                name="only-dependency",
                requirements=[
                    python_requirement("only-dependency==1.0.0"),
                ],
            )
            """
        )

    def test_creates_a_build_file_with_all_dependencies_listed(self) -> None:
        all_dependencies = [
            Dependency(
                "top-dependency",
                "top_dependency",
                "1.0.0",
                dependencies=[
                    Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
                    Dependency("subdependency", "subdependency", "0.1.0"),
                    Dependency(
                        "subdependency-with-same-second-level",
                        "subdependency-with-same-second-level",
                        "0.2.0",
                    ),
                ],
            ),
            Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
            Dependency(
                "subdependency",
                "subdependency",
                "0.1.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            Dependency(
                "subdependency-with-same-second-level",
                "subdependency-with-same-second-level",
                "0.2.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
        ]

        build_string = create_build_file(all_dependencies, ["top-dependency"])

        assert build_string == textwrap.dedent(
            # language=python
            """
            python_requirement_library(
                name="top_dependency",
                requirements=[
                    python_requirement("top_dependency==1.0.0"),
                    python_requirement("second-level-dependency==0.2.0"),
                    python_requirement("subdependency==0.1.0"),
                    python_requirement("subdependency-with-same-second-level==0.2.0"),
                ],
            )
            """
        )

    def test_creates_build_file_with_multiple_target_dependencies(self) -> None:
        all_dependencies = [
            Dependency("attrs", "attrs", "18.1.0"),
            Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
            Dependency(
                "subdependency",
                "subdependency",
                "0.1.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            Dependency(
                "subdependency-with-same-second-level",
                "subdependency-with-same-second-level",
                "0.2.0",
                dependencies=[Dependency("second-level-dependency", "second-level-dependency", "0.2.0")],
            ),
            Dependency(
                "top-dependency",
                "top_dependency",
                "1.0.0",
                dependencies=[
                    Dependency("second-level-dependency", "second-level-dependency", "0.2.0"),
                    Dependency("subdependency", "subdependency", "0.1.0"),
                    Dependency(
                        "subdependency-with-same-second-level",
                        "subdependency-with-same-second-level",
                        "0.2.0",
                    ),
                ],
            ),
        ]

        build_string = create_build_file(all_dependencies, ["attrs", "top-dependency"])

        assert build_string == textwrap.dedent(
            # language=python
            """
            python_requirement_library(
                name="attrs",
                requirements=[
                    python_requirement("attrs==18.1.0"),
                ],
            )
            
            
            python_requirement_library(
                name="top_dependency",
                requirements=[
                    python_requirement("top_dependency==1.0.0"),
                    python_requirement("second-level-dependency==0.2.0"),
                    python_requirement("subdependency==0.1.0"),
                    python_requirement("subdependency-with-same-second-level==0.2.0"),
                ],
            )
            """
        )


class TestMain:
    def test_create_build_file_from_pipfile_and_graph(self, tmpdir: path.local) -> None:
        tmp_path = Path(str(tmpdir))
        pipfile = tmp_path / "Pipfile"
        pipfile_graph = tmp_path / "Pipfile.lock.graph-tree"
        build_file = tmp_path / "BUILD"
        pipfile.write_text(
            textwrap.dedent(
                # language=toml
                """
                [[source]]
                name = "pypi"
                url = "https://pypi.org/simple"
                verify_ssl = true
                
                [dev-packages]
                
                [packages]
                top-dependency = "*"
                """
            )
        )
        pipfile_graph.write_text(
            json.dumps(
                list(
                    map(
                        asdict,
                        [
                            _dependency(
                                "top-dependency",
                                "2.0.0",
                                package_name="top_dependency",
                                dependencies=[
                                    _package("subdependency", "0.1.0"),
                                    _package("subdependency-with-same-second-level", "0.2.0"),
                                ],
                            ),
                            _dependency(
                                "subdependency",
                                "0.1.0",
                                [_package("second-level-dependency", "second-level-dependency", "0.2.0")],
                            ),
                            _dependency(
                                "subdependency-with-same-second-level",
                                "0.2.0",
                                [_package("second-level-dependency", "second-level-dependency", "0.2.0")],
                            ),
                            _dependency("second-level-dependency", "0.2.0"),
                        ],
                    )
                )
            )
        )

        main(pipfile, pipfile_graph, build_file)

        assert (
            build_file.read_text()
            == textwrap.dedent(
                """
            # Generated by tools/pipenv_graph_to_build.py. See README for how to regenerate.
            python_requirement_library(
                name="top_dependency",
                requirements=[
                    python_requirement("top_dependency==2.0.0"),
                    python_requirement("second-level-dependency==0.2.0"),
                    python_requirement("subdependency==0.1.0"),
                    python_requirement("subdependency-with-same-second-level==0.2.0"),
                ],
            )
            """
            ).lstrip()
        )
