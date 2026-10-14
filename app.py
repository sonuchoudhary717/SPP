from flask import Flask, render_template, request, Response
import pickle
import mysql.connector
import csv
import io
import os

app = Flask(__name__)

# =====================================
# LOAD MACHINE LEARNING MODEL
# =====================================

with open("model.pkl", "rb") as file:
    model = pickle.load(file)


# =====================================
# MYSQL CONNECTION
# =====================================

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "student_prediction"),
        ssl_disabled=False
    )
# =====================================
# HOME
# =====================================

@app.route("/")
def home():
    return render_template("index.html")


# =====================================
# STUDENT PERFORMANCE PREDICTION
# =====================================

@app.route("/predict", methods=["GET", "POST"])
def predict():

    if request.method == "GET":
        return render_template("index.html")

    connection = None
    cursor = None

    try:
        student_name = request.form.get(
            "student_name", ""
        ).strip()

        student_id = request.form.get(
            "student_id", ""
        ).strip()

        study_hours = float(request.form.get("study_hours", ""))
        attendance = float(request.form.get("attendance", ""))
        previous_marks = float(
            request.form.get("previous_marks", "")
        )
        assignments = float(request.form.get("assignments", ""))

        if not student_name or not student_id:
            return "Please enter student name and student ID.", 400

        if not 0 <= study_hours <= 24:
            return "Study hours must be between 0 and 24.", 400

        if not 0 <= attendance <= 100:
            return "Attendance must be between 0 and 100.", 400

        if not 0 <= previous_marks <= 100:
            return "Previous marks must be between 0 and 100.", 400

        if not 0 <= assignments <= 100:
            return "Assignment score must be between 0 and 100.", 400

        # Features must follow the model's training order.
        features = [[
            study_hours,
            attendance,
            previous_marks,
            assignments
        ]]

        predicted_score = float(model.predict(features)[0])
        predicted_score = round(
            max(0, min(100, predicted_score)), 2
        )

        # Performance category and advice
        if predicted_score >= 85:
            performance = "Excellent"
            advice = (
                "Excellent work! Keep maintaining "
                "your performance."
            )
        elif predicted_score >= 70:
            performance = "Good"
            advice = (
                "Good performance. Continue regular study."
            )
        elif predicted_score >= 50:
            performance = "Average"
            advice = (
                "Practice regularly and improve "
                "your study routine."
            )
        else:
            performance = "Needs Improvement"
            advice = (
                "Focus on attendance, assignments "
                "and daily revision."
            )

        # Save prediction to MySQL
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO predictions (
                student_name,
                student_id,
                study_hours,
                attendance,
                previous_marks,
                assignments,
                predicted_score,
                performance,
                advice
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            student_name,
            student_id,
            study_hours,
            attendance,
            previous_marks,
            assignments,
            predicted_score,
            performance,
            advice
        ))

        connection.commit()

        return render_template(
            "index.html",
            prediction=predicted_score,
            predicted_score=predicted_score,
            performance=performance,
            advice=advice,
            student_name=student_name,
            student_id=student_id
        )

    except (ValueError, TypeError):
        return "Please enter valid numeric values.", 400

    except Exception as e:
        app.logger.exception("Prediction failed: %s", e)

        if connection and connection.is_connected():
            connection.rollback()

        return (
            "Prediction failed. Check the VS Code terminal."
        ), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================
# HISTORY + SEARCH + FILTER
# =====================================

@app.route("/history")
def history():

    connection = None
    cursor = None

    try:
        search = request.args.get("search", "").strip()
        performance = request.args.get("performance", "").strip()

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = "SELECT * FROM predictions WHERE 1=1"
        values = []

        if search:
            sql += """
                AND (
                    student_name LIKE %s
                    OR CAST(student_id AS CHAR) LIKE %s
                )
            """

            values.extend([
                "%" + search + "%",
                "%" + search + "%"
            ])

        allowed_performances = [
            "Excellent",
            "Good",
            "Average",
            "Needs Improvement"
        ]

        if performance in allowed_performances:
            sql += " AND performance = %s"
            values.append(performance)

        sql += " ORDER BY created_at DESC"

        cursor.execute(sql, tuple(values))
        records = cursor.fetchall()

        return render_template(
            "history.html",
            records=records
        )

    except Exception as e:
        app.logger.exception("History failed: %s", e)

        return (
            "History could not load. Check the VS Code terminal."
        ), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================
# INDIVIDUAL STUDENT REPORT
# =====================================

@app.route("/report/<int:student_id>")
def student_report(student_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # student_id here is the prediction table's record ID.
        cursor.execute(
            "SELECT * FROM predictions WHERE id = %s",
            (student_id,)
        )

        record = cursor.fetchone()

        if not record:
            return "Student report not found.", 404

        return render_template(
            "student_report.html",
            record=record,
            student=record
        )

    except Exception as e:
        app.logger.exception("Student report failed: %s", e)

        return "Student report could not load.", 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================
# DASHBOARD
# =====================================

@app.route("/dashboard")
def dashboard():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Total predictions and average score
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(
                    ROUND(AVG(predicted_score), 2), 0
                ) AS average
            FROM predictions
        """)

        summary = cursor.fetchone() or {}

        total = int(summary.get("total") or 0)
        average = float(summary.get("average") or 0)

        # 2. Excellent students
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM predictions
            WHERE performance = 'Excellent'
        """)

        excellent = int(
            (cursor.fetchone() or {}).get("count") or 0
        )

        # 3. Students needing improvement
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM predictions
            WHERE performance = 'Needs Improvement'
        """)

        needs_improvement = int(
            (cursor.fetchone() or {}).get("count") or 0
        )

        # 4. Performance distribution chart
        cursor.execute("""
            SELECT performance, COUNT(*) AS count
            FROM predictions
            GROUP BY performance
            ORDER BY CASE performance
                WHEN 'Excellent' THEN 1
                WHEN 'Good' THEN 2
                WHEN 'Average' THEN 3
                WHEN 'Needs Improvement' THEN 4
                ELSE 5
            END
        """)

        distribution = cursor.fetchall() or []

        performance_labels = [
            str(row.get("performance") or "Unknown")
            for row in distribution
        ]

        performance_counts = [
            int(row.get("count") or 0)
            for row in distribution
        ]

        # 5. Recent 10 student predictions
        cursor.execute("""
            SELECT *
            FROM predictions
            ORDER BY created_at DESC
            LIMIT 10
        """)

        recent_records = cursor.fetchall() or []

        return render_template(
            "dashboard.html",
            total=total,
            total_students=total,
            average=average,
            average_score=average,
            avg_score=average,
            excellent=excellent,
            excellent_count=excellent,
            needs_improvement=needs_improvement,
            needs_improvement_count=needs_improvement,
            performance_labels=performance_labels,
            performance_counts=performance_counts,
            distribution=distribution,
            performance_data=distribution,
            recent_records=recent_records
        )

    except Exception as e:
        app.logger.exception("Dashboard failed: %s", e)

        return (
            "Dashboard could not load. Check the VS Code terminal."
        ), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================
# EXPORT PREDICTIONS TO CSV
# =====================================

@app.route("/export-csv")
def export_csv():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                student_name,
                student_id,
                study_hours,
                attendance,
                previous_marks,
                assignments,
                predicted_score,
                performance,
                advice,
                created_at
            FROM predictions
            ORDER BY created_at DESC
        """)

        records = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Record ID",
            "Student Name",
            "Student ID",
            "Study Hours",
            "Attendance",
            "Previous Marks",
            "Assignment Score",
            "Predicted Score",
            "Performance",
            "Advice",
            "Created At"
        ])

        for record in records:
            writer.writerow([
                record.get("id"),
                record.get("student_name"),
                record.get("student_id"),
                record.get("study_hours"),
                record.get("attendance"),
                record.get("previous_marks"),
                record.get("assignments"),
                record.get("predicted_score"),
                record.get("performance"),
                record.get("advice"),
                record.get("created_at")
            ])

        # UTF-8 BOM helps Excel display text correctly.
        csv_content = "\ufeff" + output.getvalue()

        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition":
                    "attachment; filename=student_predictions.csv"
            }
        )

    except Exception as e:
        app.logger.exception("CSV export failed: %s", e)

        return "CSV export failed. Check the VS Code terminal.", 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# =====================================
# RUN FLASK APPLICATION
# =====================================

if __name__ == "__main__":
    app.run(debug=True)