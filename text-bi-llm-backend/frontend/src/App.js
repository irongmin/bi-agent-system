import React, { useState } from "react";
import "./App.css";
import axios from "axios";

function App() {
  const [question, setQuestion] = useState("작년과 올해 수주금액 비교해줘");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    setLoading(true);
    setAnswer("");

    try {
      const res = await axios.post("http://localhost:8000/test-llm", {
        question,
      });
      setAnswer(res.data.answer);
    } catch (err) {
      console.error(err);
      setAnswer(
        "분석 중 오류가 발생했습니다. (백엔드 서버가 꺼져 있거나 CORS/네트워크 문제일 수 있습니다.)"
      );
    } finally {
      setLoading(false);
    }
  };

  const setTemplate = (text) => {
    setQuestion(text);
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-title">일지테크 · AI 구매 BI 데모</div>
        <div className="header-right">
          PoC 환경
          <span className="badge">DEV</span>
        </div>
      </header>

      <div className="body">
        <aside className="sidebar">
          <div>
            <div className="sidebar-title">메뉴</div>
            <div className="nav-section">
              <div className="nav-item active">📊 대시보드</div>
              <div className="nav-item">🕒 분석 히스토리</div>
              <div className="nav-item">📑 리포트 요약 (준비중)</div>
            </div>
          </div>
          <div>
            <div className="sidebar-title">자주 쓰는 분석</div>
            <div className="template-section">
              <button
                className="template-button"
                onClick={() =>
                  setTemplate("연도별 수주금액 추세와 증가율을 요약해줘.")
                }
              >
                연도별 수주금액 비교
              </button>
              <button
                className="template-button"
                onClick={() =>
                  setTemplate("최근 1년 동안 공급사별 TOP 10 발주금액을 요약해줘.")
                }
              >
                공급사별 TOP 10 발주금액
              </button>
              <button
                className="template-button"
                onClick={() =>
                  setTemplate("품목별 월별 수주 추세를 한 줄로 요약해줘.")
                }
              >
                품목별 월별 수주 추세
              </button>
            </div>
          </div>
        </aside>

        <main className="main">
          {/* 오늘의 질문 섹션 */}
          <section className="section-card">
            <div className="section-title">
              오늘의 질문
              <span className="tag">질의 모드</span>
            </div>
            <div
              style={{
                marginTop: "6px",
                fontSize: "12px",
                color: "#6b7280",
              }}
            >
              자연어로 질문하면 AI가 SQL을 만들고, 결과를 자동으로 시각화합니다.
            </div>
            <div className="query-row">
              <input
                className="query-input"
                placeholder="예: 작년과 올해 수주금액 비교해줘"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
              <button
                className="button-primary"
                onClick={handleAnalyze}
                disabled={loading}
              >
                {loading ? "AI 분석 중..." : "AI 분석 실행"}
              </button>
            </div>
          </section>

          {/* 요약 인사이트 & KPI */}
          <section className="section-card">
            <div className="section-title">요약 인사이트 &amp; KPI</div>
            <div className="summary-layout">
              <div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#9ca3af",
                    marginBottom: "4px",
                  }}
                >
                  AI 인사이트 요약
                </div>
                <p className="insight-text">
                  {answer
                    ? answer
                    : "왼쪽 상단에서 질문을 입력하고 'AI 분석 실행'을 누르면, 여기에서 AI가 요약한 인사이트가 표시됩니다."}
                </p>
              </div>
              <div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#9ca3af",
                    marginBottom: "4px",
                  }}
                >
                  핵심 KPI
                </div>
                <div className="kpi-grid">
                  <div className="kpi-card">
                    <div className="kpi-label">2024 수주금액</div>
                    <div className="kpi-value">₩ 12.0억</div>
                    <div className="kpi-sub">기준: Mock 데이터</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-label">2025 수주금액</div>
                    <div className="kpi-value">₩ 14.8억</div>
                    <div className="kpi-sub">+23.4% YoY (Mock)</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-label">주요 공급사 수</div>
                    <div className="kpi-value">8</div>
                    <div className="kpi-sub">상위 80% 기여 (Mock)</div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 결과 상세 (여긴 아직 Mock으로 두자) */}
          <section className="section-card">
            <div className="section-title">결과 상세</div>
            <div className="bottom-layout">
              <div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#9ca3af",
                    marginBottom: "4px",
                  }}
                >
                  연도별 수주금액 차트(Mock)
                </div>
                <div className="mock-chart" />
              </div>
              <div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#9ca3af",
                    marginBottom: "4px",
                  }}
                >
                  데이터 테이블(Mock)
                </div>
                <table className="table">
                  <thead>
                    <tr>
                      <th>연도</th>
                      <th>수주금액</th>
                      <th>증감률</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>2024</td>
                      <td>1,203,200,000</td>
                      <td>-</td>
                    </tr>
                    <tr>
                      <td>2025</td>
                      <td>1,485,500,000</td>
                      <td>+23.4%</td>
                    </tr>
                  </tbody>
                </table>
                <div
                  style={{
                    marginTop: "10px",
                    fontSize: "12px",
                    color: "#9ca3af",
                  }}
                >
                  실제 서비스에서는 이 영역에 MySQL 조회 결과가 표시됩니다.
                </div>
              </div>
            </div>

            <div
              style={{
                marginTop: "12px",
                fontSize: "12px",
                color: "#9ca3af",
              }}
            >
              생성된 SQL (참고용 / 지금은 고정 Mock)
            </div>
            <div className="sql-box">
              {`SELECT year, SUM(order_qty * unit_price) AS total_amount
FROM fact_purchase_order
WHERE year IN (2024, 2025)
GROUP BY year
ORDER BY year;`}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
