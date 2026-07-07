"""B2B 마크다운 리포트 정적 파일링·보존 생명주기 관리."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import aiofiles
import aiofiles.os

logger = logging.getLogger(__name__)

# 환경 변수 SSOT
STORAGE_DIR_ENV = "STORAGE_DIR"
REPORT_RETENTION_DAYS_ENV = "REPORT_RETENTION_DAYS"
DEFAULT_STORAGE_DIR = "storage/reports/"
DEFAULT_REPORT_RETENTION_DAYS = 30
REPORT_FILENAME_PREFIX = "synapse_report_"
REPORT_FILENAME_SUFFIX = ".md"
_REPORT_DATE_PATTERN = re.compile(
    rf"^{re.escape(REPORT_FILENAME_PREFIX)}(\d{{4}}-\d{{2}}-\d{{2}})"
    rf"{re.escape(REPORT_FILENAME_SUFFIX)}$"
)


@dataclass(frozen=True, slots=True)
class ReportFileResult:
    """리포트 파일 저장 결과."""

    file_path: Path
    written: bool
    size_bytes: int
    skipped_existing: bool = False


@dataclass(frozen=True, slots=True)
class PurgeResult:
    """만료 리포트 청소 결과."""

    retention_days: int
    cutoff_date: date
    files_deleted: int
    dirs_removed: int
    bytes_freed: int
    errors: int


def resolve_repo_root() -> Path:
    """모노레포 루트(synapse-platform) 절대 경로."""
    # backend/app/utils/report_filer.py → parents[3] == repo root
    return Path(__file__).resolve().parents[3]


def resolve_storage_root(storage_dir: str | None = None) -> Path:
    """STORAGE_DIR 환경 변수를 모노레포 루트 기준 절대 경로로 해석한다."""
    raw = (storage_dir or os.getenv(STORAGE_DIR_ENV) or DEFAULT_STORAGE_DIR).strip()
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (resolve_repo_root() / path).resolve()


def report_filename_for_date(target_date: date) -> str:
    """일자별 규격 파일명 — synapse_report_YYYY-MM-DD.md"""
    return f"{REPORT_FILENAME_PREFIX}{target_date.isoformat()}{REPORT_FILENAME_SUFFIX}"


def report_relative_path(target_date: date) -> Path:
    """연/월 하위 상대 경로 — storage/reports/2026/07/synapse_report_2026-07-02.md"""
    return Path(
        str(target_date.year),
        f"{target_date.month:02d}",
        report_filename_for_date(target_date),
    )


def parse_report_date_from_filename(name: str) -> date | None:
    """파일명에서 분석 기준일을 파싱한다."""
    match = _REPORT_DATE_PATTERN.match(name)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


class ReportFiler:
    """리포트 마크다운 비동기 파일 저장·만료 청소 전담 유틸리티."""

    def __init__(self, storage_root: Path | None = None) -> None:
        self._storage_root = storage_root or resolve_storage_root()

    @property
    def storage_root(self) -> Path:
        return self._storage_root

    def resolve_absolute_path(self, target_date: date) -> Path:
        """대상 일자 리포트의 절대 저장 경로."""
        return self._storage_root / report_relative_path(target_date)

    async def ensure_directory(self, directory: Path) -> None:
        """디렉토리가 없으면 비동기로 생성한다."""
        try:
            await aiofiles.os.makedirs(directory, exist_ok=True)
        except PermissionError:
            logger.exception(
                "[report_filer] 디렉토리 생성 권한 없음 path=%s",
                directory,
            )
            raise
        except OSError:
            logger.exception(
                "[report_filer] 디렉토리 생성 실패 path=%s",
                directory,
            )
            raise

    async def read_report(self, target_date: date) -> str | None:
        """대상 일자 리포트 마크다운을 비동기로 읽는다. 없으면 None."""
        path = self.resolve_absolute_path(target_date)
        if not path.exists():
            return None
        try:
            async with aiofiles.open(path, mode="r", encoding="utf-8") as handle:
                return await handle.read()
        except OSError:
            logger.exception(
                "[report_filer] 파일 읽기 실패 path=%s",
                path,
            )
            return None

    async def save_report(
        self,
        target_date: date,
        markdown: str,
        *,
        overwrite: bool = False,
    ) -> ReportFileResult:
        """마크다운 리포트를 연/월 경로에 비동기 저장한다.

        Idempotency: 동일 일자 파일이 이미 존재하고 overwrite=False이면
        쓰기를 건너뛰고 기존 파일 메타를 반환한다.
        원자성: .md.tmp 임시 파일 작성 후 os.replace로 교체한다.
        """
        destination = self.resolve_absolute_path(target_date)
        await self.ensure_directory(destination.parent)

        if destination.exists() and not overwrite:
            size_bytes = await self._file_size(destination)
            logger.info(
                "[report_filer] 기존 파일 유지(Idempotent) path=%s size=%d",
                destination,
                size_bytes,
            )
            return ReportFileResult(
                file_path=destination,
                written=False,
                size_bytes=size_bytes,
                skipped_existing=True,
            )

        temp_path = destination.with_suffix(f"{REPORT_FILENAME_SUFFIX}.tmp")
        content = markdown if markdown.endswith("\n") else f"{markdown}\n"

        try:
            async with aiofiles.open(temp_path, mode="w", encoding="utf-8") as handle:
                await handle.write(content)
            await asyncio.to_thread(os.replace, temp_path, destination)
            size_bytes = await self._file_size(destination)
        except PermissionError:
            logger.exception(
                "[report_filer] 파일 쓰기 권한 없음 path=%s",
                destination,
            )
            await self._safe_unlink(temp_path)
            raise
        except OSError:
            logger.exception(
                "[report_filer] 파일 저장 실패 path=%s",
                destination,
            )
            await self._safe_unlink(temp_path)
            raise

        logger.info(
            "[report_filer] 저장 완료 path=%s size=%d bytes",
            destination,
            size_bytes,
        )
        return ReportFileResult(
            file_path=destination,
            written=True,
            size_bytes=size_bytes,
            skipped_existing=False,
        )

    async def purge_expired_reports(
        self,
        retention_days: int | None = None,
    ) -> PurgeResult:
        """보존 기간이 지난 리포트 .md 파일과 빈 디렉토리를 재귀 삭제한다."""
        days = retention_days
        if days is None:
            days = int(
                os.getenv(REPORT_RETENTION_DAYS_ENV, DEFAULT_REPORT_RETENTION_DAYS)
            )
        if days < 0:
            msg = "retention_days must be >= 0"
            raise ValueError(msg)

        cutoff = date.today() - timedelta(days=days)
        files_deleted = 0
        bytes_freed = 0
        errors = 0

        if not self._storage_root.exists():
            logger.info(
                "[report_filer][purge] 스토리지 루트 없음 — skip root=%s",
                self._storage_root,
            )
            return PurgeResult(
                retention_days=days,
                cutoff_date=cutoff,
                files_deleted=0,
                dirs_removed=0,
                bytes_freed=0,
                errors=0,
            )

        # 파일 삭제 — 스토리지 루트 하위 전체 탐색
        for file_path in await asyncio.to_thread(self._iter_report_files):
            report_date = parse_report_date_from_filename(file_path.name)
            if report_date is None:
                continue
            if report_date >= cutoff:
                continue

            try:
                size = file_path.stat().st_size
                await aiofiles.os.remove(file_path)
                files_deleted += 1
                bytes_freed += size
                logger.info(
                    "[report_filer][purge] 만료 파일 삭제 path=%s date=%s",
                    file_path,
                    report_date.isoformat(),
                )
            except PermissionError:
                errors += 1
                logger.exception(
                    "[report_filer][purge] 삭제 권한 없음 path=%s",
                    file_path,
                )
            except OSError:
                errors += 1
                logger.exception(
                    "[report_filer][purge] 파일 삭제 실패 path=%s",
                    file_path,
                )

        dirs_removed = await asyncio.to_thread(
            self._remove_empty_directories,
            self._storage_root,
        )

        logger.info(
            "[report_filer][purge] 완료 retention_days=%d cutoff=%s "
            "deleted=%d dirs_removed=%d freed=%d errors=%d",
            days,
            cutoff.isoformat(),
            files_deleted,
            dirs_removed,
            bytes_freed,
            errors,
        )
        return PurgeResult(
            retention_days=days,
            cutoff_date=cutoff,
            files_deleted=files_deleted,
            dirs_removed=dirs_removed,
            bytes_freed=bytes_freed,
            errors=errors,
        )

    def _iter_report_files(self) -> list[Path]:
        """스토리지 트리에서 synapse_report_*.md 파일 목록을 수집한다."""
        matches: list[Path] = []
        for root, _dirs, files in os.walk(self._storage_root):
            for name in files:
                if _REPORT_DATE_PATTERN.match(name):
                    matches.append(Path(root) / name)
        return matches

    @staticmethod
    def _remove_empty_directories(root: Path) -> int:
        """하위부터 빈 디렉토리를 재귀 제거한다 (루트 자체는 유지)."""
        removed = 0
        for current_root, dirnames, filenames in os.walk(root, topdown=False):
            current = Path(current_root)
            if current == root:
                continue
            if dirnames or filenames:
                continue
            try:
                current.rmdir()
                removed += 1
                logger.debug("[report_filer][purge] 빈 디렉토리 삭제 path=%s", current)
            except PermissionError:
                logger.warning(
                    "[report_filer][purge] 디렉토리 삭제 권한 없음 path=%s",
                    current,
                )
            except OSError:
                logger.warning(
                    "[report_filer][purge] 빈 디렉토리 삭제 실패 path=%s",
                    current,
                )
        return removed

    @staticmethod
    async def _file_size(path: Path) -> int:
        return await asyncio.to_thread(lambda: path.stat().st_size)

    @staticmethod
    async def _safe_unlink(path: Path) -> None:
        if not path.exists():
            return
        try:
            await aiofiles.os.remove(path)
        except OSError:
            logger.warning("[report_filer] 임시 파일 삭제 실패 path=%s", path)
