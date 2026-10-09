---
theme: default
title: 문서 제목
colorSchema: light
fonts:
  sans: Noto Sans CJK KR
  mono: Noto Sans Mono CJK KR
  provider: none
canvasWidth: 980
aspectRatio: 16/9
drawings:
  enabled: false
layout: none
---

<div style="position:absolute;inset:0;padding:56px 64px;display:flex;flex-direction:column;justify-content:center;background:linear-gradient(135deg,#f0f9ff 0%,#ffffff 60%)">
  <div class="muted" style="font-size:14px;font-weight:700;letter-spacing:.08em">공유 자료</div>
  <div style="font-size:40px;font-weight:800;line-height:1.25;margin-top:14px">문서 제목</div>
  <div style="font-size:22px;font-weight:700;margin-top:8px;color:#0369a1">한 줄 부제</div>
  <div class="sm muted" style="margin-top:16px">YYYY-MM-DD 기준 · 작성자</div>
</div>

---

# 흐름 한눈에 보기 <span class="sub">좌→우, 화면 폭을 다 쓴다</span>

<div class="flow">
  <div class="box"><div class="tag">1</div><div style="font-size:20px;font-weight:800;margin-top:8px">입력</div><div class="sm">무엇을 받는가</div></div>
  <div class="arrow">→</div>
  <div class="box accent"><div class="tag">2</div><div style="font-size:20px;font-weight:800;margin-top:8px">처리</div><div class="sm">무엇을 판단하는가</div></div>
  <div class="arrow">→</div>
  <div class="box"><div class="tag">3</div><div style="font-size:20px;font-weight:800;margin-top:8px">결과</div><div class="sm">누가 무엇을 받는가</div></div>
</div>

---

# 두 안 비교

<div class="grid2" style="height:320px">
  <div class="box"><div style="font-size:19px;font-weight:800">A안</div><ul class="sm"><li>장점</li><li>비용</li></ul></div>
  <div class="box accent"><div style="font-size:19px;font-weight:800">B안 (제안)</div><ul class="sm"><li>장점</li><li>비용</li></ul></div>
</div>

---

# 수치는 표로

<table class="t">
<thead><tr><th>항목</th><th>지난주</th><th>이번 주</th><th>메모</th></tr></thead>
<tbody>
<tr><td>지표 A</td><td>12</td><td>15</td><td>근거: <a href="https://example.com">대시보드</a></td></tr>
<tr><td>지표 B</td><td>3</td><td>2</td><td>—</td></tr>
</tbody>
</table>

---

# 부록 — 용어

<table class="t">
<thead><tr><th style="width:200px">용어</th><th>뜻</th></tr></thead>
<tbody>
<tr><td><b>용어 1</b></td><td>한 줄 정의</td></tr>
<tr><td><b>용어 2</b></td><td>한 줄 정의</td></tr>
</tbody>
</table>
