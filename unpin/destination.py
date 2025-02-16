import typing
from zipfile import ZipFile
from pathlib import Path, PurePath
import os
import shutil

from .util import PathsPair


class DestinationBackend:
	__slots__ = ()

	def getFileText(self, pp: PathsPair) -> str:
		raise NotImplementedError

	def writeBack(self, pp: PathsPair, source: str) -> None:
		raise NotImplementedError

	def iterPaths(self, path: Path) -> typing.Iterator[PurePath]:
		raise NotImplementedError

	@classmethod
	def make(cls, patchee: Path) -> "DestinationBackend":
		if patchee.is_dir():
			return DirDestinationBackend()
		return ArchiveDestinationBackend()


class DirDestinationBackend(DestinationBackend):
	__slots__ = ()

	def _iterPaths(self, path: Path):
		for el in path.iterdir():
			if el.is_dir():
				yield from self._iterPaths(el)
			else:
				yield el

	def iterPaths(self, path: Path) -> typing.Iterator[PurePath]:
		for el in self._iterPaths(path):
			yield el.relative_to(path)

	def getFileText(self, pp: PathsPair) -> str:
		return (pp.root / pp.internal).read_text()

	def writeBack(self, pp: PathsPair, source: str) -> None:
		(pp.root / pp.internal).write_text(source)


class ArchiveDestinationBackend(DestinationBackend):
	__slots__ = ()

	def iterPaths(self, path: Path) -> typing.Iterator[PurePath]:
		with ZipFile(path) as a:
			for name in a.namelist():
				yield PurePath(name)

	def getFileText(self, pp: PathsPair) -> str:
		with ZipFile(pp.root) as a:
			appConstsText = a.read(str(pp.internal))
			return appConstsText.decode("utf-8")

	def writeBack(self, pp: PathsPair, source: str) -> None:
		with ZipFile(str(pp.root) + '.patched', 'w') as dst:
			with ZipFile(pp.root, 'r') as src:
				metadata_info = None
				for info in src.infolist():
					if info.filename == str(pp.internal):
						print(f"Found file to replace {info.filename}")
						metadata_info = info
					elif info.is_dir():
						dst.mkdir(info)
					else:
						dst.writestr(info, src.read(info.filename))
			if metadata_info is not None:
				dst.writestr(metadata_info, source)
			else:
				dst.writestr(str(pp.internal), source)
		os.unlink(pp.root)
		shutil.move(str(pp.root) + '.patched', pp.root)
