from __future__ import annotations

from sqlalchemy import Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class ConnectionProfile(Base):
    __tablename__ = "connection_profiles"

    port: Mapped[str] = mapped_column(Text, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(Text)
    serial_number: Mapped[str | None] = mapped_column(Text)
    vid: Mapped[str | None] = mapped_column(Text)
    pid: Mapped[str | None] = mapped_column(Text)
    is_esp32: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    last_connected_at: Mapped[str] = mapped_column(Text, nullable=False)


class WirelessProfile(Base):
    __tablename__ = "wireless_profiles"

    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    identifier: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column("metadata", Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    last_connected_at: Mapped[str] = mapped_column(Text, nullable=False)


class OperationAudit(Base):
    __tablename__ = "operation_audit"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(Text, nullable=False)
    identifier: Mapped[str] = mapped_column(Text, nullable=False)
    operation_id: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    preview: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False)


class PrototypeProjectRecord(Base):
    __tablename__ = "prototype_projects"

    identifier: Mapped[str] = mapped_column(Text, primary_key=True)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    project_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class InspectionSnapshot(Base):
    __tablename__ = "inspection_snapshots"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    inspection_json: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False)


class TestResultRecord(Base):
    __tablename__ = "test_results"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    test_id: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[str] = mapped_column(Text, nullable=False)


class VisualEvidenceRecord(Base):
    __tablename__ = "visual_evidence"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    image_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    marking: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_ppm: Mapped[int] = mapped_column(Integer, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_at: Mapped[str] = mapped_column(Text, nullable=False)
