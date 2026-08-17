/**
 * Format timestamps into exact human-readable time slots and relative time.
 */

export function formatExactTimeSlot(isoString) {
  if (!isoString) return { date: 'N/A', time: 'N/A', relative: '', slot: 'N/A' };

  try {
    let str = String(isoString);
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-')) {
      str = str + 'Z';
    }

    const d = new Date(str);
    if (isNaN(d.getTime())) return { date: 'Invalid Date', time: '', relative: '', slot: '' };

    // Format Date: e.g. "Aug 15, 2026"
    const dateStr = d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });

    // Format Exact Time: e.g. "11:03:45 PM"
    const timeStr = d.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });

    // Calculate 15-minute time slot block
    const hours = d.getHours();
    const minutes = d.getMinutes();
    const slotStartMin = Math.floor(minutes / 15) * 15;
    const slotEndMin = (slotStartMin + 15) % 60;
    const slotEndHour = slotStartMin + 15 >= 60 ? (hours + 1) % 24 : hours;

    const pad = (num) => String(num).padStart(2, '0');
    const slotStr = `${pad(hours)}:${pad(slotStartMin)} - ${pad(slotEndHour)}:${pad(slotEndMin)}`;

    // Calculate Relative Time
    const now = new Date();
    const diffSecs = Math.floor((now.getTime() - d.getTime()) / 1000);
    let relativeStr = '';

    if (diffSecs < 10 && diffSecs >= -5) {
      relativeStr = 'Just now';
    } else if (diffSecs < 60 && diffSecs >= 0) {
      relativeStr = `${diffSecs}s ago`;
    } else if (diffSecs < 3600 && diffSecs >= 0) {
      const mins = Math.floor(diffSecs / 60);
      relativeStr = `${mins}m ago`;
    } else if (diffSecs < 86400 && diffSecs >= 0) {
      const hoursDiff = Math.floor(diffSecs / 3600);
      relativeStr = `${hoursDiff}h ago`;
    } else if (diffSecs >= 86400) {
      const days = Math.floor(diffSecs / 86400);
      relativeStr = `${days}d ago`;
    }

    return {
      date: dateStr,
      time: timeStr,
      slot: slotStr,
      full: `${dateStr} at ${timeStr} (${slotStr})`,
      relative: relativeStr,
    };
  } catch (e) {
    return { date: String(isoString), time: '', relative: '', slot: '' };
  }
}

