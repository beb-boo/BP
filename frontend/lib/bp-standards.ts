export type BPLimits = {
    ageGroup: string;
    sysMax: number;
    diaMax: number;
};

// Calculate age from Date of Birth
export function calculateAge(dob: string | Date | undefined): number {
    if (!dob) return 30; // Default to adult if unknown
    const birthDate = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
        age--;
    }
    return age;
}

// Get BP Limits based on Age
// Criteria provided by User:
// Infants: <= 90/60
// 3-6y: <= 110/70
// 7-17y: <= 120/80
// 18-59y: <= 140/90
// 60+y: <= 160/90
export function getBPLimits(age: number): BPLimits {
    if (age < 3) {
        return { ageGroup: "Infant", sysMax: 90, diaMax: 60 };
    } else if (age <= 6) {
        return { ageGroup: "Child (3-6)", sysMax: 110, diaMax: 70 };
    } else if (age <= 17) {
        return { ageGroup: "Child (7-17)", sysMax: 120, diaMax: 80 };
    } else if (age < 60) {
        return { ageGroup: "Adult", sysMax: 140, diaMax: 90 };
    } else {
        return { ageGroup: "Elderly", sysMax: 160, diaMax: 90 };
    }
}

export function getBPColor(sys: number, dia: number, limits: BPLimits): string {
    // Return color status based on limits
    // Simple logic: Red if above limit
    if (sys > limits.sysMax || dia > limits.diaMax) {
        return "#ef4444"; // Red
    }
    return "#10b981"; // Green (Normal)
}
