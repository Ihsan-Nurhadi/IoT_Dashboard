'use client';
import React, { useState } from 'react';
import { FileDown, Calendar, X, Download, ChevronLeft, ChevronRight } from 'lucide-react';

interface ExportModalProps {
    isOpen: boolean;
    onClose: () => void;
    onExport: (startDate: Date | null, endDate: Date | null) => void;
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const DAYS = ['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA'];

function CalendarView({
    selectedDate,
    currentMonth,
    currentYear,
    onSelectDate,
    onMonthChange,
    onYearChange,
    accentColor,
    isStart
}: {
    selectedDate: Date | null;
    currentMonth: number;
    currentYear: number;
    onSelectDate: (date: Date | null) => void;
    onMonthChange: (month: number) => void;
    onYearChange: (year: number) => void;
    accentColor: string;
    isStart: boolean;
}) {
    const handlePrevMonth = () => {
        if (currentMonth === 0) {
            onMonthChange(11);
            onYearChange(currentYear - 1);
        } else {
            onMonthChange(currentMonth - 1);
        }
    };

    const handleNextMonth = () => {
        if (currentMonth === 11) {
            onMonthChange(0);
            onYearChange(currentYear + 1);
        } else {
            onMonthChange(currentMonth + 1);
        }
    };

    const handleToday = () => {
        const today = new Date();
        onSelectDate(today);
        onMonthChange(today.getMonth());
        onYearChange(today.getFullYear());
    };

    const handleClear = () => {
        onSelectDate(null);
    };

    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay();
    const daysInPrevMonth = new Date(currentYear, currentMonth, 0).getDate();

    const calendarGrid = [];
    let dayCount = 1;
    let nextMonthDayCount = 1;

    for (let i = 0; i < 6; i++) {
        const week = [];
        for (let j = 0; j < 7; j++) {
            if (i === 0 && j < firstDayOfMonth) {
                const prevMonthDate = new Date(currentYear, currentMonth - 1, daysInPrevMonth - firstDayOfMonth + j + 1);
                week.push({ day: prevMonthDate.getDate(), isCurrentMonth: false, date: prevMonthDate });
            } else if (dayCount <= daysInMonth) {
                const d = new Date(currentYear, currentMonth, dayCount);
                week.push({ day: dayCount, isCurrentMonth: true, date: d });
                dayCount++;
            } else {
                const nextMonthDate = new Date(currentYear, currentMonth + 1, nextMonthDayCount);
                week.push({ day: nextMonthDayCount, isCurrentMonth: false, date: nextMonthDate });
                nextMonthDayCount++;
            }
        }
        calendarGrid.push(week);
    }

    const formatDateInput = (d: Date | null) => {
        if (!d) return 'Not selected';
        const day = d.getDate().toString().padStart(2, '0');
        const monthStr = d.toLocaleString('en-GB', { month: 'short' });
        const year = d.getFullYear();
        return `${day} ${monthStr} ${year}`;
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{
                    width: '32px', height: '32px',
                    borderRadius: '8px',
                    background: isStart ? 'rgba(14, 189, 181, 0.1)' : 'rgba(139, 92, 246, 0.1)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: accentColor
                }}>
                    <Calendar size={16} />
                </div>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.05em', color: '#f8fafc' }}>
                    {isStart ? 'START DATE' : 'END DATE'}
                </span>
            </div>

            <div style={{
                padding: '0.875rem 1rem',
                background: 'rgba(255, 255, 255, 0.03)',
                border: selectedDate ? `1px solid ${accentColor}` : '1px solid rgba(255, 255, 255, 0.05)',
                borderRadius: '8px',
                fontSize: '0.9rem',
                fontWeight: 600,
                color: selectedDate ? '#f8fafc' : '#52627a'
            }}>
                {formatDateInput(selectedDate)}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 0.5rem' }}>
                    <button onClick={handlePrevMonth} style={{ color: '#8493a8', cursor: 'pointer', background: 'transparent', border: 'none', padding: '0.25rem' }}>
                        <ChevronLeft size={18} />
                    </button>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f8fafc' }}>
                        {MONTHS[currentMonth]} <span style={{ color: accentColor }}>{currentYear}</span>
                    </div>
                    <button onClick={handleNextMonth} style={{ color: '#8493a8', cursor: 'pointer', background: 'transparent', border: 'none', padding: '0.25rem' }}>
                        <ChevronRight size={18} />
                    </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '0.25rem' }}>
                    {DAYS.map(d => (
                        <div key={d} style={{ textAlign: 'center', fontSize: '0.75rem', fontWeight: 600, color: '#52627a', paddingBottom: '0.5rem' }}>
                            {d}
                        </div>
                    ))}
                    {calendarGrid.map((week, i) => (
                        <React.Fragment key={i}>
                            {week.map((dayObj, j) => {
                                const isSelected = selectedDate &&
                                    dayObj.date.getDate() === selectedDate.getDate() &&
                                    dayObj.date.getMonth() === selectedDate.getMonth() &&
                                    dayObj.date.getFullYear() === selectedDate.getFullYear();

                                return (
                                    <div key={`${i}-${j}`} style={{ display: 'flex', justifyContent: 'center' }}>
                                        <button
                                            onClick={() => onSelectDate(dayObj.date)}
                                            style={{
                                                width: '32px',
                                                height: '32px',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                borderRadius: '8px',
                                                fontSize: '0.85rem',
                                                fontWeight: isSelected ? 700 : 500,
                                                color: isSelected ? '#ffffff' : (dayObj.isCurrentMonth ? '#8493a8' : '#2d3748'),
                                                background: isSelected ? accentColor : 'transparent',
                                                cursor: 'pointer',
                                                border: isSelected && isStart ? '1px solid #14b8a6' : 'none',
                                                transition: 'all 0.1s ease',
                                            }}
                                            onMouseEnter={(e) => {
                                                if (!isSelected && dayObj.isCurrentMonth) {
                                                    e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                                                }
                                            }}
                                            onMouseLeave={(e) => {
                                                if (!isSelected) {
                                                    e.currentTarget.style.background = 'transparent';
                                                }
                                            }}
                                        >
                                            {dayObj.day}
                                        </button>
                                    </div>
                                );
                            })}
                        </React.Fragment>
                    ))}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1rem' }}>
                    <button
                        onClick={handleClear}
                        style={{ fontSize: '0.8rem', fontWeight: 500, color: '#8493a8', background: 'transparent', border: 'none', cursor: 'pointer' }}
                        onMouseEnter={(e) => e.currentTarget.style.color = '#f8fafc'}
                        onMouseLeave={(e) => e.currentTarget.style.color = '#8493a8'}
                    >
                        Clear
                    </button>
                    <button
                        onClick={handleToday}
                        style={{ fontSize: '0.8rem', fontWeight: 700, color: accentColor, background: 'transparent', border: 'none', cursor: 'pointer' }}
                    >
                        Today
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function ExportModal({ isOpen, onClose, onExport }: ExportModalProps) {
    const today = new Date();
    const [startDate, setStartDate] = useState<Date | null>(null);
    const [endDate, setEndDate] = useState<Date | null>(today);

    const [startMonth, setStartMonth] = useState<number>(today.getMonth());
    const [startYear, setStartYear] = useState<number>(today.getFullYear());

    const [endMonth, setEndMonth] = useState<number>(today.getMonth());
    const [endYear, setEndYear] = useState<number>(today.getFullYear());

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999
        }}>
            <div style={{
                background: '#131b29',
                backgroundImage: 'linear-gradient(135deg, #161f30 0%, #101622 100%)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '16px',
                width: '100%',
                maxWidth: '750px',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
            }}>
                <div style={{
                    padding: '1.25rem 1.75rem',
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between'
                }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <div style={{
                            width: '42px', height: '42px',
                            borderRadius: '10px',
                            background: 'rgba(14, 189, 181, 0.1)',
                            border: '1px solid rgba(14, 189, 181, 0.2)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: '#0ebdb5'
                        }}>
                            <FileDown size={20} />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <h2 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 700, color: '#f8fafc' }}>Export Report</h2>
                            <p style={{ margin: 0, fontSize: '0.8125rem', color: '#8493a8', marginTop: '0.1rem' }}>Select a date range to export</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{ color: '#8493a8', background: 'transparent', border: 'none', cursor: 'pointer', padding: '0.5rem' }}
                        onMouseEnter={(e) => e.currentTarget.style.color = '#f8fafc'}
                        onMouseLeave={(e) => e.currentTarget.style.color = '#8493a8'}
                    >
                        <X size={20} />
                    </button>
                </div>

                <div style={{ display: 'flex', padding: '1.75rem' }}>
                    <div style={{ flex: 1, paddingRight: '1.75rem', borderRight: '1px solid rgba(255, 255, 255, 0.05)' }}>
                        <CalendarView
                            selectedDate={startDate}
                            currentMonth={startMonth}
                            currentYear={startYear}
                            onSelectDate={setStartDate}
                            onMonthChange={setStartMonth}
                            onYearChange={setStartYear}
                            accentColor="#0ebdb5"
                            isStart={true}
                        />
                    </div>
                    <div style={{ flex: 1, paddingLeft: '1.75rem' }}>
                        <CalendarView
                            selectedDate={endDate}
                            currentMonth={endMonth}
                            currentYear={endYear}
                            onSelectDate={setEndDate}
                            onMonthChange={setEndMonth}
                            onYearChange={setEndYear}
                            accentColor="#8b5cf6"
                            isStart={false}
                        />
                    </div>
                </div>

                <div style={{
                    padding: '1.25rem 1.75rem',
                    borderTop: '1px solid rgba(255,255,255,0.05)',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '1rem',
                    background: 'rgba(0,0,0,0.1)'
                }}>
                    <button
                        onClick={onClose}
                        style={{
                            padding: '0.625rem 1.25rem',
                            borderRadius: '8px',
                            background: 'transparent',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: '#f8fafc',
                            fontSize: '0.875rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => onExport(startDate, endDate)}
                        style={{
                            padding: '0.625rem 1.5rem',
                            borderRadius: '8px',
                            background: '#0ebdb5',
                            border: 'none',
                            color: '#ffffff',
                            fontSize: '0.875rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            boxShadow: '0 4px 12px rgba(14, 189, 181, 0.3)'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#14b8a6'}
                        onMouseLeave={(e) => e.currentTarget.style.background = '#0ebdb5'}
                    >
                        <Download size={16} /> Export
                    </button>
                </div>
            </div>
        </div>
    );
}
