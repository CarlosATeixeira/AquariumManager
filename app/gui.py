from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPalette, QPen, QTextOption
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import Aquarium, Fish, Task
from .simulation import SimulationEngine


class AquariumVisualizer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setFrameShape(QFrame.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self._bounds = QRectF(0.0, 0.0, 640.0, 360.0)
        gradient = QLinearGradient(self._bounds.topLeft(), self._bounds.bottomLeft())
        gradient.setColorAt(0.0, QColor("#1f5fa6"))
        gradient.setColorAt(1.0, QColor("#071c33"))
        self._background = self._scene.addRect(self._bounds, QPen(Qt.NoPen), gradient)
        self._fish_nodes: Dict[int, tuple[QGraphicsEllipseItem, QGraphicsSimpleTextItem, float]] = {}
        self._velocities: Dict[int, QPointF] = {}
        self._random = random.Random()
        self._label_font = QFont("Segoe UI", 9)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._view.fitInView(self._bounds, Qt.KeepAspectRatio)

    def clear(self) -> None:
        for body, label, _ in self._fish_nodes.values():
            self._scene.removeItem(body)
            self._scene.removeItem(label)
        self._fish_nodes.clear()
        self._velocities.clear()
        self._view.fitInView(self._bounds, Qt.KeepAspectRatio)

    def _brush_for(self, fish: Fish) -> QLinearGradient:
        health_ratio = max(0.0, min(1.0, fish.health / 100.0))
        hunger_ratio = max(0.0, min(1.0, fish.hunger / 100.0))
        base = QColor.fromHsvF(0.58 - health_ratio * 0.24, 0.5 + hunger_ratio * 0.35, 0.92)
        gradient = QLinearGradient(0.0, 0.0, 1.0, 1.0)
        gradient.setCoordinateMode(QLinearGradient.ObjectMode)
        gradient.setColorAt(0.0, base.lighter(130))
        gradient.setColorAt(1.0, base.darker(120))
        return gradient

    def sync(self, fishes: list[Fish]) -> None:
        active_ids = {fish.id for fish in fishes if fish.id is not None}
        for fish_id in list(self._fish_nodes.keys()):
            if fish_id not in active_ids:
                body, label, _ = self._fish_nodes.pop(fish_id)
                self._scene.removeItem(body)
                self._scene.removeItem(label)
                self._velocities.pop(fish_id, None)
        for fish in fishes:
            if fish.id is None:
                continue
            size = 32.0 + (fish.health / 100.0) * 14.0
            node = self._fish_nodes.get(fish.id)
            if node is None:
                x = self._random.uniform(self._bounds.left() + 60.0, self._bounds.right() - 60.0)
                y = self._random.uniform(self._bounds.top() + 60.0, self._bounds.bottom() - 60.0)
                body = self._scene.addEllipse(0.0, 0.0, size, size * 0.55, QPen(Qt.NoPen))
                body.setBrush(self._brush_for(fish))
                body.setPos(x, y)
                label = self._scene.addSimpleText("", self._label_font)
                label.setBrush(QColor("#f0f4ff"))
                label.setPos(x, y + size * 0.6)
                self._fish_nodes[fish.id] = (body, label, size)
                speed = 1.4 + (100.0 - fish.hunger) * 0.016
                angle = self._random.uniform(0.0, 360.0)
                vx = speed * math.cos(math.radians(angle))
                vy = speed * math.sin(math.radians(angle))
                self._velocities[fish.id] = QPointF(vx, vy)
            else:
                body, label, previous_size = node
                if abs(previous_size - size) > 0.8:
                    body.setRect(0.0, 0.0, size, size * 0.55)
                    self._fish_nodes[fish.id] = (body, label, size)
                body.setBrush(self._brush_for(fish))
        for fish in fishes:
            if fish.id is None or fish.id not in self._fish_nodes:
                continue
            body, label, size = self._fish_nodes[fish.id]
            label.setText(f"{fish.name} • Saúde {int(fish.health)}%")
            pos = body.pos()
            label.setPos(pos.x(), pos.y() + size * 0.6)
        self._view.fitInView(self._bounds, Qt.KeepAspectRatio)

    def step(self) -> None:
        for fish_id, node in list(self._fish_nodes.items()):
            body, label, size = node
            velocity = self._velocities.get(fish_id)
            if velocity is None:
                continue
            if self._random.random() < 0.025:
                direction = math.degrees(math.atan2(velocity.y(), velocity.x()))
                delta = self._random.uniform(-18.0, 18.0)
                speed = math.hypot(velocity.x(), velocity.y())
                direction += delta
                velocity = QPointF(speed * math.cos(math.radians(direction)), speed * math.sin(math.radians(direction)))
            pos = body.pos() + velocity
            width = size
            height = size * 0.55
            if pos.x() <= self._bounds.left() or pos.x() + width >= self._bounds.right():
                velocity.setX(-velocity.x())
                pos.setX(max(self._bounds.left(), min(self._bounds.right() - width, pos.x())))
            if pos.y() <= self._bounds.top() or pos.y() + height >= self._bounds.bottom():
                velocity.setY(-velocity.y())
                pos.setY(max(self._bounds.top(), min(self._bounds.bottom() - height, pos.y())))
            self._velocities[fish_id] = velocity
            body.setPos(pos)
            label.setPos(pos.x(), pos.y() + size * 0.6)


class AquariumWindow(QMainWindow):
    def __init__(self, simulation: SimulationEngine) -> None:
        super().__init__()
        self._simulation = simulation
        self._selected_aquarium: Optional[int] = None
        self._education_data = self._build_education_data()
        self._suppress_fish_selection = False
        self._visualizer = AquariumVisualizer()
        self._aquarium_list = QListWidget()
        self._temperature_spin = QDoubleSpinBox()
        self._fish_table = QTableWidget(0, 4)
        self._task_table = QTableWidget(0, 4)
        self._education_text = QTextEdit()
        self._metric_temperature = QLabel("--")
        self._metric_cleanliness = QLabel("--")
        self._metric_population = QLabel("--")
        self._metric_next_task = QLabel("--")
        self._status = QStatusBar()
        self._build_window()
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(40)
        self._animation_timer.timeout.connect(self._visualizer.step)
        self._animation_timer.start()
        self._simulation_timer = QTimer(self)
        self._simulation_timer.setInterval(2500)
        self._simulation_timer.timeout.connect(self._handle_simulation_tick)
        self._simulation_timer.start()
        self._refresh_aquariums()

    def _build_window(self) -> None:
        self.setWindowTitle("Simulador de Aquários Escolares")
        self.resize(1360, 820)
        self.setMinimumSize(1100, 720)
        self.setStatusBar(self._status)
        self._status.setStyleSheet("QStatusBar { background-color: #09142a; color: #f0f4ff; padding: 6px; }")
        self.setStyleSheet(
            """
            QWidget { background-color: #081a30; color: #f0f4ff; font-family: 'Segoe UI'; font-size: 11pt; }
            QListWidget { background-color: #0f2c4d; border: 1px solid #1c3c66; border-radius: 12px; padding: 6px; }
            QListWidget::item { padding: 10px; margin: 4px; border-radius: 10px; }
            QListWidget::item:selected { background-color: #1d5aa6; }
            QPushButton { background-color: #1d5aa6; border: none; border-radius: 12px; padding: 10px; color: #f0f4ff; }
            QPushButton:hover { background-color: #2a6fc9; }
            QPushButton:disabled { background-color: #1a2f4f; color: #8ba3c9; }
            QFrame#panelFrame { background-color: rgba(16, 42, 76, 0.85); border-radius: 20px; border: 1px solid #1b3c60; padding: 12px; }
            QTableWidget { background: transparent; border: none; selection-background-color: rgba(42, 111, 201, 160); selection-color: #f0f4ff; padding: 6px; }
            QTableWidget::item { background-color: transparent; border: none; padding: 6px; }
            QHeaderView::section { background-color: #153558; color: #f0f4ff; padding: 8px; border: none; }
            QTextEdit { background-color: rgba(15, 44, 77, 0.9); border: 1px solid #1c3c66; border-radius: 18px; padding: 18px; }
            QDoubleSpinBox { background-color: #0f2c4d; border: 1px solid #1c3c66; border-radius: 12px; padding: 6px 46px 6px 12px; color: #f0f4ff; }
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button { border: none; background: transparent; width: 24px; }
            QDoubleSpinBox::up-button { subcontrol-origin: padding; subcontrol-position: top right; margin: 1px 4px 0 0; }
            QDoubleSpinBox::down-button { subcontrol-origin: padding; subcontrol-position: bottom right; margin: 0 4px 1px 0; }
            QFrame#metricsFrame { background-color: rgba(16, 42, 76, 0.85); border-radius: 20px; border: 1px solid #1b3c60; }
            QFrame#educationFrame { background-color: rgba(16, 42, 76, 0.85); border-radius: 20px; border: 1px solid #1b3c60; }
            QLabel#metricLabel { font-size: 12pt; font-weight: 400; background-color: rgba(29, 90, 166, 0.25); border-radius: 14px; padding: 8px 14px; }
            QLabel#metricValue { font-size: 18pt; font-weight: 600; background-color: rgba(29, 90, 166, 0.25); border-radius: 14px; padding: 8px 14px; }
            """
        )
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 16)
        main_layout.setSpacing(18)
        sidebar = self._build_sidebar()
        content = self._build_content()
        main_layout.addWidget(sidebar, 1)
        main_layout.addWidget(content, 3)

    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setSpacing(14)
        title = QLabel("Aquários")
        title.setFont(QFont("Segoe UI", 14, QFont.Medium))
        layout.addWidget(title)
        self._aquarium_list.setSelectionMode(QListWidget.SingleSelection)
        self._aquarium_list.currentItemChanged.connect(self._on_aquarium_changed)
        layout.addWidget(self._aquarium_list, 1)
        button_add = QPushButton("Novo aquário")
        button_add.clicked.connect(self._handle_add_aquarium)
        layout.addWidget(button_add)
        button_remove = QPushButton("Remover aquário")
        button_remove.clicked.connect(self._handle_remove_aquarium)
        layout.addWidget(button_remove)
        controls = QFrame()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setSpacing(10)
        temp_row = QHBoxLayout()
        temp_label = QLabel("Meta de temperatura")
        temp_label.setObjectName("metricLabel")
        controls_layout.addWidget(temp_label)
        temp_box = QHBoxLayout()
        self._temperature_spin.setRange(16.0, 32.0)
        self._temperature_spin.setDecimals(1)
        self._temperature_spin.setSingleStep(0.5)
        self._temperature_spin.setSuffix(" °C")
        temp_box.addWidget(self._temperature_spin, 1)
        button_temp = QPushButton("Aplicar")
        button_temp.clicked.connect(self._handle_temperature)
        temp_box.addWidget(button_temp)
        controls_layout.addLayout(temp_box)
        button_feed = QPushButton("Alimentar agora")
        button_feed.clicked.connect(self._handle_feed)
        controls_layout.addWidget(button_feed)
        button_clean = QPushButton("Registrar limpeza")
        button_clean.clicked.connect(self._handle_clean)
        controls_layout.addWidget(button_clean)
        button_add_fish = QPushButton("Adicionar peixe")
        button_add_fish.clicked.connect(self._handle_add_fish)
        controls_layout.addWidget(button_add_fish)
        button_remove_fish = QPushButton("Remover peixe")
        button_remove_fish.clicked.connect(self._handle_remove_fish)
        controls_layout.addWidget(button_remove_fish)
        button_add_task = QPushButton("Nova rotina")
        button_add_task.clicked.connect(self._handle_add_task)
        controls_layout.addWidget(button_add_task)
        button_complete_task = QPushButton("Confirmar rotina")
        button_complete_task.clicked.connect(self._handle_complete_task)
        controls_layout.addWidget(button_complete_task)
        layout.addWidget(controls)
        layout.addStretch()
        return panel

    def _build_content(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        layout.addWidget(self._visualizer, 3)
        layout.addWidget(self._build_metrics_frame(), 0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_fish_panel())
        splitter.addWidget(self._build_task_panel())
        splitter.addWidget(self._build_education_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 3)
        layout.addWidget(splitter, 4)
        return panel

    def _build_metrics_frame(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("metricsFrame")
        frame.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(28)
        layout.addLayout(self._build_metric_block("Temperatura", self._metric_temperature))
        layout.addLayout(self._build_metric_block("Limpeza", self._metric_cleanliness))
        layout.addLayout(self._build_metric_block("Habitantes", self._metric_population))
        layout.addLayout(self._build_metric_block("Próxima rotina", self._metric_next_task))
        return frame

    def _build_metric_block(self, label: str, value_label: QLabel) -> QVBoxLayout:
        block = QVBoxLayout()
        title = QLabel(label)
        title.setObjectName("metricLabel")
        value_label.setObjectName("metricValue")
        block.addWidget(title)
        block.addWidget(value_label)
        return block

    def _build_fish_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("panelFrame")
        frame.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        title = QLabel("Peixes")
        title.setFont(QFont("Segoe UI", 12, QFont.Medium))
        layout.addWidget(title)
        self._fish_table.setHorizontalHeaderLabels(["Nome", "Espécie", "Fome", "Saúde"])
        self._fish_table.horizontalHeader().setStretchLastSection(True)
        self._fish_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._fish_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._fish_table.setSelectionMode(QTableWidget.SingleSelection)
        self._fish_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._fish_table.verticalHeader().setVisible(False)
        self._fish_table.itemSelectionChanged.connect(self._on_fish_selection)
        layout.addWidget(self._fish_table, 1)
        return frame

    def _build_task_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("panelFrame")
        frame.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        title = QLabel("Rotinas")
        title.setFont(QFont("Segoe UI", 12, QFont.Medium))
        layout.addWidget(title)
        self._task_table.setHorizontalHeaderLabels(["Tarefa", "Intervalo", "Próxima", "Status"])
        self._task_table.horizontalHeader().setStretchLastSection(True)
        self._task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._task_table.setSelectionMode(QTableWidget.SingleSelection)
        self._task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._task_table.verticalHeader().setVisible(False)
        self._task_table.itemSelectionChanged.connect(self._on_task_selection)
        layout.addWidget(self._task_table, 1)
        return frame

    def _build_education_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("educationFrame")
        frame.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        title = QLabel("Vida na água")
        title.setFont(QFont("Segoe UI", 12, QFont.Medium))
        layout.addWidget(title)
        self._education_text.setReadOnly(True)
        self._education_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self._education_text.setAttribute(Qt.WA_StyledBackground, True)
        layout.addWidget(self._education_text, 1)
        return frame

    def _build_education_data(self) -> Dict[str, str]:
        return {
            "Peixe-palhaço": "Criam parceria com anêmonas e dependem de água estável e limpa.",
            "Tetra Neon": "Vivem em cardume, precisam de água limpa e luz suave para reduzir o estresse.",
            "Guppy": "Reproduzem com facilidade, ideal monitorar quantidade e temperatura constante.",
            "Corydora": "Habitam o fundo e ajudam a manter o aquário limpo com alimentação equilibrada.",
            "Betta": "Respiram diretamente do ar e precisam de espaços tranquilos sem correntes fortes.",
            "Molinésia": "Tolera pequenas variações de salinidade e reforça conversas sobre ecossistemas costeiros.",
            "Disco": "Sensível à qualidade da água, incentiva disciplina com testes e manutenções.",
        }

    def _handle_simulation_tick(self) -> None:
        self._simulation.tick()
        self._refresh_aquariums()
        self._refresh_details()

    def _current_aquarium(self) -> Optional[Aquarium]:
        if self._selected_aquarium is None:
            return None
        for aquarium in self._simulation.aquariums():
            if aquarium.id == self._selected_aquarium:
                return aquarium
        return None

    def _on_aquarium_changed(self, current: Optional[QListWidgetItem]) -> None:
        if current is None:
            self._selected_aquarium = None
            self._visualizer.clear()
            self._fish_table.setRowCount(0)
            self._task_table.setRowCount(0)
            self._metric_temperature.setText("--")
            self._metric_cleanliness.setText("--")
            self._metric_population.setText("--")
            self._metric_next_task.setText("--")
            self._education_text.clear()
            return
        aquarium_id = current.data(Qt.UserRole)
        if aquarium_id is None:
            return
        self._selected_aquarium = int(aquarium_id)
        self._refresh_details()

    def _refresh_aquariums(self) -> None:
        previous = self._selected_aquarium
        self._aquarium_list.blockSignals(True)
        self._aquarium_list.clear()
        for aquarium in self._simulation.aquariums():
            if aquarium.id is None:
                continue
            text = f"{aquarium.name}\n{aquarium.current_temperature:.1f}°C • {aquarium.cleanliness:.0f}% limpeza"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, aquarium.id)
            self._aquarium_list.addItem(item)
            if previous is not None and aquarium.id == previous:
                self._aquarium_list.setCurrentItem(item)
        self._aquarium_list.blockSignals(False)
        if self._aquarium_list.currentItem() is None and self._aquarium_list.count() > 0:
            self._aquarium_list.setCurrentRow(0)

    def _refresh_details(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            self._visualizer.clear()
            self._fish_table.setRowCount(0)
            self._task_table.setRowCount(0)
            self._metric_temperature.setText("--")
            self._metric_cleanliness.setText("--")
            self._metric_population.setText("--")
            self._metric_next_task.setText("--")
            self._education_text.clear()
            return
        fishes = self._simulation.fish_for(aquarium.id)
        tasks = self._simulation.tasks_for(aquarium.id)
        self._update_metrics(aquarium, fishes, tasks)
        self._update_fish_table(fishes)
        self._update_task_table(tasks)
        self._update_education(fishes)
        self._visualizer.sync(fishes)
        if not self._temperature_spin.hasFocus():
            self._temperature_spin.blockSignals(True)
            self._temperature_spin.setValue(aquarium.target_temperature)
            self._temperature_spin.blockSignals(False)

    def _update_metrics(self, aquarium: Aquarium, fishes: list[Fish], tasks: list[Task]) -> None:
        self._metric_temperature.setText(f"{aquarium.current_temperature:.1f}°C / {aquarium.target_temperature:.1f}°C")
        self._metric_cleanliness.setText(f"{aquarium.cleanliness:.0f}%")
        self._metric_population.setText(str(len(fishes)))
        next_label = "--"
        now = datetime.now(timezone.utc)
        soonest: Optional[tuple[Task, datetime]] = None
        for task in tasks:
            due = task.last_run_at + timedelta(minutes=task.interval_minutes)
            if soonest is None or due < soonest[1]:
                soonest = (task, due)
        if soonest is not None:
            task, due = soonest
            if due <= now:
                next_label = "Agora"
            else:
                remaining = due - now
                minutes = int(remaining.total_seconds() // 60)
                hours = minutes // 60
                minutes %= 60
                if hours > 0:
                    next_label = f"{hours}h {minutes}min"
                else:
                    next_label = f"{minutes}min"
        self._metric_next_task.setText(next_label)
        self._status.showMessage(f"Aquário {aquarium.name} em {aquarium.current_temperature:.1f}°C e limpeza {aquarium.cleanliness:.0f}%.", 5000)

    def _update_fish_table(self, fishes: list[Fish]) -> None:
        previous = self._fish_table.currentRow()
        self._suppress_fish_selection = True
        self._fish_table.setRowCount(len(fishes))
        for row, fish in enumerate(fishes):
            hunger_item = QTableWidgetItem(f"{int(fish.hunger)}%")
            hunger_item.setTextAlignment(Qt.AlignCenter)
            health_item = QTableWidgetItem(f"{int(fish.health)}%")
            health_item.setTextAlignment(Qt.AlignCenter)
            self._fish_table.setItem(row, 0, QTableWidgetItem(fish.name))
            self._fish_table.setItem(row, 1, QTableWidgetItem(fish.species))
            self._fish_table.setItem(row, 2, hunger_item)
            self._fish_table.setItem(row, 3, health_item)
        self._suppress_fish_selection = False
        if 0 <= previous < len(fishes):
            self._fish_table.selectRow(previous)
        else:
            self._fish_table.clearSelection()

    def _update_task_table(self, tasks: list[Task]) -> None:
        now = datetime.now(timezone.utc)
        self._task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            interval_item = QTableWidgetItem(f"{task.interval_minutes} min")
            interval_item.setTextAlignment(Qt.AlignCenter)
            due_at = task.last_run_at + timedelta(minutes=task.interval_minutes)
            if due_at <= now:
                remaining_text = "Agora"
                status_text = "Atrasada"
                color = QColor(255, 92, 92, 120)
            else:
                remaining = due_at - now
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                if hours > 0:
                    remaining_text = f"{hours}h {minutes}min"
                else:
                    remaining_text = f"{minutes} min"
                status_text = "No prazo"
                color = QColor(42, 121, 196, 70)
            remaining_item = QTableWidgetItem(remaining_text)
            remaining_item.setTextAlignment(Qt.AlignCenter)
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            self._task_table.setItem(row, 0, QTableWidgetItem(task.kind.capitalize()))
            self._task_table.setItem(row, 1, interval_item)
            self._task_table.setItem(row, 2, remaining_item)
            self._task_table.setItem(row, 3, status_item)
            for column in range(4):
                item = self._task_table.item(row, column)
                if item is not None:
                    item.setBackground(color)

    def _update_education(self, fishes: list[Fish]) -> None:
        self._set_general_education(fishes)

    def _set_general_education(self, fishes: list[Fish]) -> None:
        hints = []
        seen: Dict[str, bool] = {}
        for fish in fishes:
            if fish.species not in seen:
                seen[fish.species] = True
                info = self._education_data.get(fish.species)
                if info:
                    hints.append(f"{fish.species}: {info}")
        if not hints:
            hints.append("Adicione novas espécies para desbloquear curiosidades e conectar cuidados com a ODS Vida na Água.")
        self._education_text.setPlainText("\n\n".join(hints))

    def _show_species_details(self, fish: Fish) -> None:
        tip = self._education_data.get(fish.species)
        summary = f"Fome atual: {int(fish.hunger)}%\nSaúde atual: {int(fish.health)}%"
        if tip:
            content = f"{fish.species}\n\n{tip}\n\n{summary}"
        else:
            content = f"{fish.species}\n\n{summary}"
        self._education_text.setPlainText(content)

    def _on_fish_selection(self) -> None:
        if self._suppress_fish_selection:
            return
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            return
        row = self._fish_table.currentRow()
        fishes = self._simulation.fish_for(aquarium.id)
        if row < 0 or row >= len(fishes):
            self._set_general_education(fishes)
            return
        fish = fishes[row]
        tip = self._education_data.get(fish.species)
        if tip:
            self._status.showMessage(f"{fish.name}: {tip}", 6000)
        else:
            self._status.showMessage(f"{fish.name}: fome {int(fish.hunger)}%, saúde {int(fish.health)}%.", 6000)
        self._show_species_details(fish)

    def _on_task_selection(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            return
        row = self._task_table.currentRow()
        if row < 0:
            return
        tasks = self._simulation.tasks_for(aquarium.id)
        if row >= len(tasks):
            return
        task = tasks[row]
        due_at = task.last_run_at + timedelta(minutes=task.interval_minutes)
        now = datetime.now(timezone.utc)
        if due_at <= now:
            self._status.showMessage("Esta rotina está atrasada. Priorize sua execução com a turma.", 6000)
        else:
            remaining = due_at - now
            minutes = int(remaining.total_seconds() // 60)
            self._status.showMessage(f"Faltam aproximadamente {minutes} minutos para a próxima verificação.", 6000)

    def _handle_feed(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            QMessageBox.information(self, "Selecione um aquário", "Escolha um aquário para alimentar.")
            return
        self._simulation.feed_fish(aquarium.id)
        task = self._find_task(aquarium.id, "alimentacao")
        self._simulation.mark_task_done(task)
        self._refresh_details()
        self._status.showMessage("Alimentação registrada. Observe a recuperação dos indicadores no painel.", 6000)

    def _handle_clean(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            QMessageBox.information(self, "Selecione um aquário", "Escolha um aquário para registrar a limpeza.")
            return
        self._simulation.clean_aquarium(aquarium.id)
        task = self._find_task(aquarium.id, "limpeza")
        self._simulation.mark_task_done(task)
        self._refresh_details()
        self._status.showMessage("Limpeza concluída. A água voltou a ficar cristalina.", 6000)

    def _handle_temperature(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            QMessageBox.information(self, "Selecione um aquário", "Escolha um aquário para ajustar a temperatura.")
            return
        target = float(self._temperature_spin.value())
        self._simulation.adjust_temperature(aquarium.id, target)
        self._refresh_details()
        self._status.showMessage("Meta de temperatura atualizada. Monitore a estabilização no visor.", 6000)

    def _handle_add_aquarium(self) -> None:
        name, ok = QInputDialog.getText(self, "Novo aquário", "Nome do aquário:")
        if not ok or not name.strip():
            return
        target, ok = QInputDialog.getDouble(self, "Temperatura alvo", "Temperatura em °C:", 25.0, 16.0, 32.0, 1)
        if not ok:
            return
        aquarium = self._simulation.create_aquarium(name.strip(), float(target))
        if aquarium.id is None:
            QMessageBox.critical(self, "Erro", "Não foi possível registrar o aquário.")
            return
        self._simulation.add_task(aquarium.id, "alimentacao", 240)
        self._simulation.add_task(aquarium.id, "limpeza", 1440)
        self._simulation.add_task(aquarium.id, "temperatura", 180)
        self._selected_aquarium = aquarium.id
        self._refresh_aquariums()
        self._refresh_details()
        self._status.showMessage("Aquário criado. Cadastre peixes e monte a rotina com a turma.", 6000)

    def _handle_add_fish(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            QMessageBox.information(self, "Selecione um aquário", "Escolha um aquário para adicionar um peixe.")
            return
        name, ok = QInputDialog.getText(self, "Novo peixe", "Nome do peixe:")
        if not ok or not name.strip():
            return
        species_options = sorted(self._education_data.keys())
        if not species_options:
            QMessageBox.warning(self, "Catálogo vazio", "Nenhuma espécie cadastrada. Adicione informações na plataforma.")
            return
        species, ok = QInputDialog.getItem(self, "Espécie", "Selecione a espécie:", species_options, 0, False)
        if not ok or not species:
            return
        fish = self._simulation.create_fish(aquarium.id, name.strip(), species)
        self._refresh_details()
        tip = self._education_data.get(fish.species)
        if tip:
            QMessageBox.information(self, "Curiosidade aquática", f"{fish.species}: {tip}")
        self._status.showMessage("Peixe adicionado com sucesso. Explore as curiosidades para promover o aprendizado.", 6000)

    def _handle_remove_fish(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            QMessageBox.information(self, "Selecione um aquário", "Escolha um aquário para remover um peixe.")
            return
        row = self._fish_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selecione um peixe", "Escolha um peixe na tabela.")
            return
        fishes = self._simulation.fish_for(aquarium.id)
        if row >= len(fishes):
            return
        fish = fishes[row]
        response = QMessageBox.question(self, "Remover peixe", f"Deseja remover {fish.name}?")
        if response != QMessageBox.Yes:
            return
        if fish.id is not None:
            self._simulation.remove_fish(fish.id, aquarium.id)
        self._refresh_details()
        self._status.showMessage("Peixe removido. Aproveite para revisar o equilíbrio do ecossistema com a turma.", 6000)

    def _handle_add_task(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            QMessageBox.information(self, "Selecione um aquário", "Escolha um aquário para configurar uma rotina.")
            return
        kind, ok = QInputDialog.getText(self, "Nova rotina", "Identifique a rotina (ex: iluminação, testes de água):")
        if not ok or not kind.strip():
            return
        interval, ok = QInputDialog.getInt(self, "Intervalo", "Intervalo em minutos:", 240, 30, 2880, 10)
        if not ok:
            return
        self._simulation.add_task(aquarium.id, kind.strip().lower(), int(interval))
        self._refresh_details()
        self._status.showMessage("Rotina adicionada. Utilize-a para reforçar responsabilidade coletiva.", 6000)

    def _handle_complete_task(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            QMessageBox.information(self, "Selecione um aquário", "Escolha um aquário para marcar a rotina.")
            return
        row = self._task_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selecione uma rotina", "Escolha uma rotina na tabela.")
            return
        tasks = self._simulation.tasks_for(aquarium.id)
        if row >= len(tasks):
            return
        task = tasks[row]
        self._simulation.mark_task_done(task)
        self._refresh_details()
        self._status.showMessage("Rotina confirmada. Continue acompanhando os lembretes do painel.", 6000)

    def _find_task(self, aquarium_id: int, kind: str) -> Task:
        tasks = self._simulation.tasks_for(aquarium_id)
        for task in tasks:
            if task.kind == kind:
                return task
        return self._simulation.add_task(aquarium_id, kind, 240)

    def _handle_remove_aquarium(self) -> None:
        aquarium = self._current_aquarium()
        if aquarium is None or aquarium.id is None:
            QMessageBox.information(self, "Selecione um aquário", "Escolha um aquário para remover.")
            return
        if len(self._simulation.aquariums()) <= 1:
            QMessageBox.warning(self, "Operação negada", "Mantenha ao menos um aquário ativo para a simulação.")
            return
        response = QMessageBox.question(self, "Remover aquário", f"Deseja remover o aquário {aquarium.name}? Todos os dados serão perdidos.")
        if response != QMessageBox.Yes:
            return
        self._simulation.delete_aquarium(aquarium.id)
        self._selected_aquarium = None
        self._refresh_aquariums()
        self._refresh_details()
        self._status.showMessage("Aquário removido com sucesso.", 6000)


def run_app(simulation: SimulationEngine) -> None:
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication([])
        owns_app = True
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#081a30"))
        palette.setColor(QPalette.WindowText, QColor("#f0f4ff"))
        palette.setColor(QPalette.Base, QColor("#0f2c4d"))
        palette.setColor(QPalette.AlternateBase, QColor("#15355e"))
        palette.setColor(QPalette.Text, QColor("#f0f4ff"))
        palette.setColor(QPalette.Button, QColor("#1d5aa6"))
        palette.setColor(QPalette.ButtonText, QColor("#f0f4ff"))
        palette.setColor(QPalette.Highlight, QColor("#2a6fc9"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        app.setPalette(palette)
        app.setFont(QFont("Segoe UI", 10))
    window = AquariumWindow(simulation)
    window.show()
    if owns_app:
        app.exec()

