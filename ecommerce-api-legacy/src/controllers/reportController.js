const { PAYMENT_STATUS } = require('../config');
const enrollmentModel = require('../models/enrollmentModel');

function createReportController({ db }) {
    return {
        async financialReport() {
            const rows = await enrollmentModel.financialReportRows(db);
            const byCourse = new Map();
            for (const row of rows) {
                if (!byCourse.has(row.course_id)) {
                    byCourse.set(row.course_id, { course: row.course, revenue: 0, students: [] });
                }
                if (row.enrollment_id === null) continue; // curso sem matrículas
                const courseData = byCourse.get(row.course_id);
                if (row.status === PAYMENT_STATUS.PAID) courseData.revenue += row.amount;
                courseData.students.push({ student: row.student ?? 'Unknown', paid: row.amount ?? 0 });
            }
            return [...byCourse.values()];
        },
    };
}

module.exports = { createReportController };
