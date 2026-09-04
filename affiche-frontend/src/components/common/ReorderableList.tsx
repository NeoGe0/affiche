import type { ReactNode } from 'react';
import { useState } from 'react';
import { GripVertical } from 'lucide-react';
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type UniqueIdentifier,
} from '@dnd-kit/core';
import { restrictToParentElement, restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { moveItem } from './reorder';
import styles from './ReorderableList.module.css';

interface ReorderableListProps {

  order: string[];
  onChange: (next: string[]) => void;

  disabled?: boolean;

  label: (value: string) => string;

  renderActions?: (value: string, index: number) => ReactNode;
}

const rowId = (value: string): string => `row:${value}`;

export function ReorderableList({
  order,
  onChange,
  disabled = false,
  label,
  renderActions,
}: ReorderableListProps) {
  const [activeId, setActiveId] = useState<UniqueIdentifier | null>(null);
  const [overId, setOverId] = useState<UniqueIdentifier | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const indexOfId = (id: UniqueIdentifier | null) =>
    id === null ? -1 : order.findIndex((value) => rowId(value) === id);

  const activeIndex = indexOfId(activeId);
  const overIndex = indexOfId(overId);
  const projected =
    activeIndex >= 0 && overIndex >= 0 ? moveItem(order, activeIndex, overIndex) : order;

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id);
    setOverId(event.active.id);
  };

  const handleDragOver = (event: DragOverEvent) => {
    setOverId(event.over?.id ?? null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    setOverId(null);

    if (!over || active.id === over.id) return;

    const from = indexOfId(active.id);
    const to = indexOfId(over.id);
    const next = moveItem(order, from, to);
    if (next !== order) onChange(next);
  };

  const handleDragCancel = () => {
    setActiveId(null);
    setOverId(null);
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[restrictToVerticalAxis, restrictToParentElement]}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <SortableContext items={order.map(rowId)} strategy={verticalListSortingStrategy}>
        <ul className={styles.list}>
          {order.map((value, index) => (
            <ReorderableRow
              key={rowId(value)}
              value={value}
              label={label(value)}
              position={projected.indexOf(value) + 1}
              disabled={disabled}
            >
              {renderActions?.(value, index)}
            </ReorderableRow>
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  );
}

interface ReorderableRowProps {
  value: string;
  label: string;

  position: number;
  disabled: boolean;
  children?: ReactNode;
}

function ReorderableRow({ value, label, position, disabled, children }: ReorderableRowProps) {
  const { setNodeRef, listeners, transform, transition, isDragging } = useSortable({
    id: rowId(value),
    disabled,
  });

  return (
    <li
      ref={setNodeRef}
      className={`${styles.item} ${isDragging ? styles.dragging : ''}`}
      style={{
        transform: CSS.Translate.toString(transform),
        transition: isDragging ? undefined : transition,
      }}

      {...listeners}
    >
      <div className={styles.dragHandle}>
        <GripVertical size={16} />
      </div>
      <span className={styles.priority}>{position}</span>
      <span className={styles.name}>{label}</span>
      {children && <div className={styles.actions}>{children}</div>}
    </li>
  );
}
