import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .plot_measurement import MeasurementPlotter


class MeasurementReport:
    """Erstellt ein anschauliches Mess-Protokoll als PDF.

    Inhalte:
    - Deckblatt mit Titel, Zeitstempel und Metadaten (inkl. OpenBIS-Infos)
    - Plot-Seite (aus plot_measurement.py)
    - Messwerttabelle

    Verwendung:
        report = MeasurementReport(df, metadata)
        report.build(
            output_path="report.pdf",
            title="Komponentenmessung #123"
        )

    Erwartete DataFrame-Spalten:
    - freq_hz, level_v, u_primary, u_secondary
    - zwei Messgrößen (z.B. C/L/R/Z und D/Q/theta_deg)

    Metadaten-Struktur:
    metadata = {
        "general": {"barcode": "...", "manufacturer": "...", ...},
        "openbis": {"sample": "...", "dataset": "...", ...},
        "notes": "Freitext ..."
    }
    """

    # Spaltenname -> Einheit
    UNIT_MAP = {
        "freq_hz": "Hz",
        "level_v": "V",
        "C": "F",
        "L": "H",
        "R": "Ω",
        "Z": "Ω",
        "D": "",
        "Q": "",
        "theta_deg": "°",
        "u_primary": "",
        "u_secondary": "",
        "timestamp": "",
    }

    def __init__(self, df: pd.DataFrame, metadata: dict[str, Any] | None = None) -> None:
        self.df = df.copy()
        self.metadata = metadata or {}
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self._temp_files = []  # Liste für temporäre Dateien

    def _setup_styles(self):
        """Erstelle benutzerdefinierte Styles."""
        # Titel-Style
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        # Sektions-Überschrift
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#2c3e50"),
                spaceAfter=12,
                spaceBefore=12,
                fontName="Helvetica-Bold",
            )
        )

        # Normal mit etwas Abstand
        self.styles.add(
            ParagraphStyle(
                name="CustomBody",
                parent=self.styles["Normal"],
                fontSize=10,
                spaceAfter=6,
            )
        )

    def build(
        self,
        output_path: str | Path,
        title: str | None = None,
    ) -> Path:
        """Erstellt das PDF und gibt den Ausgabepfad zurück.

        Args:
            output_path: Zielpfad (z. B. "report.pdf").
            title: Dokumenttitel (optional). Default: automatisch generiert.

        Returns:
            Path: Pfad zur erzeugten PDF-Datei.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # PDF-Dokument erstellen
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        # Story (Inhalt) zusammenbauen
        story = []

        # 1. Deckblatt
        story.extend(self._create_cover_page(title))
        story.append(PageBreak())

        # 2. Plot-Seite
        story.extend(self._create_plot_page())
        story.append(PageBreak())

        # 3. Tabelle
        story.extend(self._create_table_page())

        # PDF bauen
        doc.build(story)

        # Temporäre Dateien löschen
        self._cleanup_temp_files()

        return output_path

    def _cleanup_temp_files(self):
        """Löscht alle temporären Dateien."""
        import contextlib
        import os

        for tmp_path in self._temp_files:
            with contextlib.suppress(OSError):
                os.remove(tmp_path)
        self._temp_files = []

    def _create_cover_page(self, title: str | None) -> list:
        """Erstellt das Deckblatt."""
        elements = []

        # Titel
        title_text = title or self._auto_title()
        elements.append(Paragraph(title_text, self.styles["CustomTitle"]))

        # Zeitstempel
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts_style = ParagraphStyle(
            name="Timestamp",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(f"Erstellt: {timestamp}", ts_style))
        elements.append(Spacer(1, 1 * cm))

        # Allgemeine Metadaten
        if self.metadata.get("general"):
            elements.append(Paragraph("Allgemeine Metadaten", self.styles["SectionHeader"]))
            elements.append(self._create_metadata_table(self.metadata["general"]))
            elements.append(Spacer(1, 0.5 * cm))

        # OpenBIS Metadaten
        if self.metadata.get("openbis"):
            elements.append(Paragraph("OpenBIS", self.styles["SectionHeader"]))
            elements.append(self._create_metadata_table(self.metadata["openbis"]))
            elements.append(Spacer(1, 0.5 * cm))

        # Notizen
        if self.metadata.get("notes"):
            elements.append(Paragraph("Notizen", self.styles["SectionHeader"]))
            elements.append(Paragraph(str(self.metadata["notes"]), self.styles["CustomBody"]))
            elements.append(Spacer(1, 0.5 * cm))

        return elements

    def _create_metadata_table(self, data: dict[str, Any]):
        """Erstellt eine formatierte Tabelle für Metadaten."""
        if not data:
            return Paragraph("(keine Daten)", self.styles["CustomBody"])

        # Daten vorbereiten
        table_data = []
        for key, value in data.items():
            table_data.append([str(key), str(value)])

        # Tabelle erstellen
        table = Table(table_data, colWidths=[5 * cm, 10 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        return table

    def _create_plot_page(self) -> list:
        """Erstellt die Plot-Seite mit MeasurementPlotter."""
        elements = []

        elements.append(Paragraph("Messergebnisse", self.styles["SectionHeader"]))

        # Plot mit MeasurementPlotter erstellen
        plotter = MeasurementPlotter(self.df)

        # Temporäre Datei für Plot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Zur Liste der temporären Dateien hinzufügen (wird nach PDF-Erstellung gelöscht)
        self._temp_files.append(tmp_path)

        # Plot erstellen und als PNG speichern
        fig, _ = plotter.plot(title="Messung", output_path=None, show=False)
        fig.set_size_inches(7, 9)  # Größe für A4
        fig.savefig(tmp_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Bild in PDF einfügen
        img = Image(tmp_path, width=15 * cm, height=18 * cm)
        elements.append(img)

        return elements

    def _create_table_page(self) -> list:
        """Erstellt die Tabellenseite mit Messwerten."""
        elements = []

        elements.append(Paragraph("Messwerte", self.styles["SectionHeader"]))

        if self.df.empty:
            elements.append(Paragraph("Keine Messwerte vorhanden", self.styles["CustomBody"]))
            return elements

        # DataFrame vorbereiten
        df = self.df.copy()

        # Timestamp formatieren
        if "timestamp" in df.columns:

            def only_time(val):
                try:
                    t = pd.to_datetime(val)
                    return t.strftime("%H:%M:%S")
                except Exception:
                    return str(val)[-8:] if pd.notnull(val) and len(str(val)) >= 8 else str(val)

            df["timestamp"] = df["timestamp"].apply(only_time)

        # level_v in mV umrechnen
        if "level_v" in df.columns:
            df["level_v"] = pd.to_numeric(df["level_v"], errors="coerce") * 1000

        # freq_hz mit SI-Präfix formatieren
        if "freq_hz" in df.columns:

            def format_freq(val):
                try:
                    v = float(val)
                except Exception:
                    return str(val)
                abs_v = abs(v)
                for factor, prefix in reversed(MeasurementPlotter.SI_PREFIXES):
                    if abs_v >= factor:
                        return f"{v / factor:.3g} {prefix}Hz" if prefix else f"{v:.3g} Hz"
                return f"{v:.3g} Hz"

            df["freq_hz"] = df["freq_hz"].apply(format_freq)

        # Spaltenüberschriften mit Einheiten
        col_labels = []
        for c in df.columns:
            if c == "freq_hz":
                col_labels.append("Frequenz")
            elif c == "level_v":
                col_labels.append("Level (mV)")
            elif c == "timestamp":
                col_labels.append("Zeit")
            else:
                einheit = self.UNIT_MAP.get(str(c), "")
                if einheit:
                    col_labels.append(f"{c} ({einheit})")
                else:
                    col_labels.append(str(c))

        # Tabellendaten vorbereiten
        table_data = [col_labels]

        # Zahlen formatieren
        for _, row in df.iterrows():
            formatted_row = []
            for val in row:
                if isinstance(val, (int, float)):
                    if pd.notna(val):
                        formatted_row.append(f"{val:.6g}")
                    else:
                        formatted_row.append("")
                else:
                    formatted_row.append(str(val))
            table_data.append(formatted_row)

        # Spaltenbreiten berechnen
        num_cols = len(col_labels)
        available_width = 17 * cm  # A4 - Ränder
        col_width = available_width / num_cols

        # Tabelle erstellen
        table = Table(table_data, colWidths=[col_width] * num_cols)
        table.setStyle(
            TableStyle(
                [
                    # Header-Style
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    # Body-Style
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 1), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                    # Alternierende Zeilen
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f8f9fa")],
                    ),
                ]
            )
        )

        elements.append(table)

        return elements

    def _auto_title(self) -> str:
        """Generiert automatisch einen Titel aus den Metadaten."""
        code = self.metadata.get("general", {}).get("barcode") or self.metadata.get(
            "general", {}
        ).get("id")
        base = "Messprotokoll"
        if code:
            return f"{base} – {code}"
        return base


# ----------------------------- CLI --------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PDF-Messprotokoll erzeugen")
    parser.add_argument("--csv", type=str, help="Pfad zur CSV-Datei", required=True)
    parser.add_argument("--out", type=str, help="Pfad zur Ausgabedatei (PDF)", default="report.pdf")
    parser.add_argument("--title", type=str, help="Dokumenttitel", default=None)
    parser.add_argument("--meta", type=str, help="Pfad zu Metadaten (JSON)", default=None)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV nicht gefunden: {csv_path}")

    csv_df = pd.read_csv(csv_path)

    meta_data = None
    if args.meta:
        meta_path = Path(args.meta)
        if not meta_path.is_file():
            raise FileNotFoundError(f"Metadaten-JSON nicht gefunden: {meta_path}")
        meta_data = json.loads(meta_path.read_text(encoding="utf-8"))

    rpt = MeasurementReport(csv_df, metadata=meta_data)
    out = rpt.build(args.out, title=args.title)
    print(f"PDF erzeugt: {out}")
