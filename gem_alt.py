import io
import math
import sys
from datetime import datetime
# pyrefly: ignore [missing-import]
import yfinance as yf  # Yahoo Finance data
import pygame
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter  # Formats FCF y-axis ticks via Convert()
from matplotlib.dates import YearLocator, DateFormatter  # Locks the stock-graph x-axis to year ticks
from pygame.locals import *

# ----------------------------------------------------------------------------
# Theme (site CSS variables) — hex for matplotlib, RGB tuples for pygame
# ----------------------------------------------------------------------------
BG_HEX, TEXT_HEX, MUTED_HEX, BORDER_HEX, TAG_HEX, ACCENT_HEX = (
    '#0a0a0a', '#f4f4f5', '#a1a1aa', '#27272a', '#18181b', '#c0392b')
BG, TEXT, MUTED, BORDER, TAG, ACCENT = (
    (10, 10, 10), (244, 244, 245), (161, 161, 170), (39, 39, 42), (24, 24, 27), (192, 57, 43))
GREEN, AMBER = (46, 204, 113), (243, 156, 18)  # Risk-gauge low / moderate bands
FONT = "inter,segoeui,consolas"  # Inter primary, Segoe UI / Consolas fallback

# ----------------------------------------------------------------------------
# Layout grid — every tab, button and input box snaps to these columns/rows
# ----------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 980, 800  # Window size
MARGIN = 50  # Left margin
BOX_W, BOX_H = 200, 50  # Standard input/button size
COL_GAP, ROW_GAP = 20, 20  # Gaps between columns / rows
COL_X = [MARGIN, MARGIN + BOX_W + COL_GAP]  # Column left edges: [50, 270]

TAB_W, TAB_H, TAB_GAP = 180, 30, 16  # Tab bar: centred pair at the top-middle
_tabs_total = 2 * TAB_W + TAB_GAP
TAB_X = [(SCREEN_W - _tabs_total) // 2 + i * (TAB_W + TAB_GAP) for i in range(2)]  # Centred horizontally
TABS_Y = 8
TABS_RULE_Y = TABS_Y + TAB_H + 4  # Horizontal rule under the tabs marking the tab bar

CONTENT_TOP = 50  # First content row (clears the tab bar + rule)


def row_y(i):  # Top of the i-th content row
    return CONTENT_TOP + i * (BOX_H + ROW_GAP)


# ----------------------------------------------------------------------------
# Matplotlib helpers — shared dark styling so every chart looks identical
# ----------------------------------------------------------------------------
def dark_axes(w, h):  # Returns a (fig, ax) pre-styled with the site theme
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(BG_HEX)
    ax.set_facecolor(BG_HEX)
    ax.tick_params(axis='x', colors=MUTED_HEX)
    ax.tick_params(axis='y', colors=MUTED_HEX)
    ax.spines['bottom'].set_color(BORDER_HEX)
    ax.spines['left'].set_color(BORDER_HEX)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    return fig, ax


def dark_legend(ax):  # Themed legend chrome
    leg = ax.legend(facecolor=TAG_HEX, edgecolor=BORDER_HEX)
    for txt in leg.get_texts():
        txt.set_color(TEXT_HEX)


def fig_to_surface(fig):  # Renders a figure to a pygame surface and closes it
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    surf = pygame.image.load(buf)
    plt.close(fig)
    return surf


def padded_ylim(ax, values):  # 5% headroom above/below the data
    lo, hi = min(values), max(values)
    pad = (hi - lo) * 0.05 if hi > lo else 1
    ax.set_ylim(lo - pad, hi + pad)


# ----------------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------------
def stock_graph(ticker_str, dates, values, n, w, h):  # Past performance, revealed up to the first n points
    try:
        if not dates:
            raise ValueError("No data")
        n = max(0, min(n, len(dates)))
        fig, ax = dark_axes(w, h)
        if n > 0:
            ax.plot(dates[:n], values[:n], color=MUTED_HEX, linewidth=1.0)
        ax.set_xlim(dates[0], dates[-1])  # Lock to the full range so the line draws into a fixed canvas
        padded_ylim(ax, values)
        ax.set_title(f"{ticker_str.upper()} : Stock Performance", color=TEXT_HEX)
        ax.xaxis.set_major_locator(YearLocator())  # One tick per year, rendered as the bare year
        ax.xaxis.set_major_formatter(DateFormatter('%Y'))
        return fig_to_surface(fig)
    except:
        return None


def fcf_graph(past_fcf_series, proj_fcf, n, w, h):  # Past (grey) + projected (red dashed) FCF, first n points
    try:
        past_pairs = []
        if past_fcf_series is not None and not past_fcf_series.empty:
            past_pairs = sorted((d.year, float(v)) for d, v in past_fcf_series.items())
        last_year = past_pairs[-1][0] if past_pairs else datetime.now().year
        proj_pairs = [(last_year + i, float(v)) for i, v in enumerate(proj_fcf or [])]
        all_pairs = past_pairs + proj_pairs
        if not all_pairs:
            raise ValueError("No data")
        n = max(0, min(n, len(all_pairs)))
        n_past = min(n, len(past_pairs))
        n_proj = max(0, n - len(past_pairs))
        fig, ax = dark_axes(w, h)
        if n_past > 0:
            ax.plot([p[0] for p in past_pairs[:n_past]], [p[1] for p in past_pairs[:n_past]],
                    color=MUTED_HEX, linewidth=1.4, marker='o', label='Past FCF')
        if n_proj > 0:
            ax.plot([p[0] for p in proj_pairs[:n_proj]], [p[1] for p in proj_pairs[:n_proj]],
                    color=ACCENT_HEX, linewidth=1.4, marker='o', linestyle='--', label='Projected FCF')
        all_xs = [p[0] for p in all_pairs]
        ax.set_xlim(min(all_xs) - 0.5, max(all_xs) + 0.5)  # Fixed frame so points pop in
        padded_ylim(ax, [p[1] for p in all_pairs])
        ax.set_title("Free Cash Flow : Past & Projected", color=TEXT_HEX)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: Convert(v)))  # Human-readable units
        if n_past > 0 or n_proj > 0:
            try:
                dark_legend(ax)
            except:
                pass
        fig.tight_layout()
        return fig_to_surface(fig)
    except:
        return None


def risk_graph(returns, w, h):  # Histogram of daily returns for the Risk Profile tab
    try:
        if not returns:
            raise ValueError("No data")
        fig, ax = dark_axes(w, h)
        ax.hist([r * 100 for r in returns], bins=40, color=MUTED_HEX, edgecolor=BORDER_HEX)
        ax.axvline(0, color=ACCENT_HEX, linewidth=1.0)  # Zero-return reference
        ax.set_title("Daily Return Distribution (1Y)", color=TEXT_HEX)
        ax.set_xlabel("Daily Return (%)", color=MUTED_HEX)
        fig.tight_layout()
        return fig_to_surface(fig)
    except:
        return None


# ----------------------------------------------------------------------------
# Finance
# ----------------------------------------------------------------------------
def Convert(num):  # Rounds and converts huge numbers to readable units
    n = abs(num)
    if n < 1e6:
        return f"{num:.2f}"
    if n < 1e9:
        return f"{num / 1e6:.2f} million"
    if n < 1e12:
        return f"{num / 1e9:.2f} billion"
    return f"{num / 1e12:.2f} trillion"


def risk_free_rate():  # 10Y US treasury yield (^TNX), 4% fallback when Yahoo returns nothing
    try:
        tnx = yf.Ticker("^TNX").history(period='5d')['Close'].dropna()
        return float(tnx.iloc[-1]) / 100 if not tnx.empty else 0.04
    except:
        return 0.04


def RiskData(ticker_str):  # Beta and risk statistics for the Risk Profile tab
    ticker = yf.Ticker(ticker_str)
    info = ticker.info
    beta = info.get("beta", None)  # CAPM systematic risk
    hist = ticker.history(period="1y")['Close'].dropna()
    if hist.empty:
        raise ValueError("No data")
    returns = hist.pct_change().dropna()
    ann_vol = float(returns.std()) * math.sqrt(252)  # Annualised volatility (252 trading days)
    ann_ret = float(hist.iloc[-1] / hist.iloc[0] - 1)  # Trailing 1Y price return
    max_dd = float((hist / hist.cummax() - 1).min())  # Largest peak-to-trough drawdown
    rf = risk_free_rate()
    sharpe = (ann_ret - rf) / ann_vol if ann_vol else 0.0  # Excess return per unit of volatility
    b = beta if beta is not None else ann_vol / 0.2  # Volatility-implied fallback when Yahoo has no beta
    category = "Low Risk" if b < 0.8 else "Moderate Risk" if b <= 1.2 else "High Risk"
    return {
        "beta": beta, "ann_vol": ann_vol, "ann_ret": ann_ret, "max_dd": max_dd,
        "sharpe": sharpe, "rf": rf, "category": category,
        "returns": list(returns.values), "name": info.get("shortName", ticker_str) or ticker_str,
    }


def get_val(df, keys):
    """Safely extracts the most recent value from a list of possible column names."""
    for key in keys:
        if key in df.columns:
            return float(df[key].iloc[0])
    return 0.0


def get_series(df, keys):
    """Safely returns a column as a Series, or a Series of zeros if missing."""
    for key in keys:
        if key in df.columns:
            return df[key].fillna(0)
    # Return a zero-filled Series matching the dataframe's index length
    return df.iloc[:, 0] * 0


def WACC(ticker_str):  # Automatically derives a WACC for the DCF
    t = yf.Ticker(ticker_str)
    i_state = t.incomestmt.T.fillna(0)

    equity = t.info.get("marketCap", 0)
    total_debt = t.info.get("totalDebt", 0)

    if equity + total_debt == 0:
        return 0.10  # Fallback WACC if Yahoo data is entirely missing

    w_equity = equity / (total_debt + equity)
    w_debt = total_debt / (total_debt + equity)
    cost_equity = risk_free_rate() + 0.05 * t.info.get("beta", 1.0)  # rf + beta * market risk premium (0.05)

    # Financials often use 'Interest Expense Non Operating'
    interest = get_val(i_state, ['Interest Expense', 'Interest Expense Non Operating'])
    cost_debt = abs(interest) / total_debt if total_debt > 0 else 0

    tax_prov = get_val(i_state, ['Tax Provision'])
    pretax = get_val(i_state, ['Pretax Income'])
    tax_r = tax_prov / pretax if pretax != 0 else 0

    return w_equity * cost_equity + w_debt * cost_debt * (1 - tax_r)


def DCF(proj_time_1, growth_r_1, p_growth_r_1, wacc_2, ebit_1, ebitda_1, ncwc_1_a, ncwc_1_b,
        cap_ex_1, tax_1, c_share_p, s_out_1, total_cash_1, total_debt_1, ticker_str):
    cap_ex_2 = [cap_ex_1]
    ebit_2 = [ebit_1]
    ebitda_2 = [ebitda_1]
    tax_2 = [tax_1]
    ncwc_b = [ncwc_1_b]
    ncwc_c = []
    fcf = []
    d_a = [ebitda_2[0] - ebit_2[0]]  # Depreciation & amortization
    growth_r_1 = float(growth_r_1) / 100
    p_growth_r_1 = float(p_growth_r_1) / 100
    present_value = []

    ncwc_c.append(ncwc_b[0] - ncwc_1_a)  # NCWC change this year vs last
    fcf.append(ebit_2[0] - tax_2[0] + cap_ex_2[0] - ncwc_c[0] + d_a[0])  # Current FCF
    present_value.append(fcf[0])

    for i in range(1, int(proj_time_1) + 1):  # Project every future FCF over the period
        ebit_2.append(ebit_2[i - 1] * (1 + growth_r_1))
        ncwc_b.append((ncwc_b[i - 1] / ebit_2[i - 1]) * ebit_2[i])  # NCWC balance for the year
        ncwc_c.append(ncwc_b[i] - ncwc_b[i - 1])  # Year-on-year NCWC change
        d_a.append(d_a[i - 1] * (1 + growth_r_1))
        cap_ex_2.append(cap_ex_2[i - 1] * (1 + growth_r_1))
        tax_2.append((tax_2[0] / ebit_2[0]) * ebit_2[i])
        fcf.append(ebit_2[i] - tax_2[i] + cap_ex_2[i] - ncwc_c[i] + d_a[i])
        present_value.append(fcf[i] / ((1 + wacc_2) ** i))  # Discounted to present value

    term_value = (fcf[int(proj_time_1)] * (1 + p_growth_r_1)) / (wacc_2 - p_growth_r_1)  # Terminal value
    ent_val = term_value / (1 + wacc_2) ** int(proj_time_1) + sum(present_value[1:])  # Enterprise value
    equ_val = ent_val + total_cash_1 - total_debt_1  # Equity value
    dis_stock_p = equ_val / s_out_1
    val_percent = (dis_stock_p - c_share_p) / c_share_p * 100  # Under/overvaluation vs current price

    out = (f"Terminal Value: {Convert(term_value)}\nImplied Enterprise Value: {Convert(ent_val)}"
           f"\nImplied Equity Value: {Convert(equ_val)}   ")
    if dis_stock_p > c_share_p:
        out += (f"\nTarget Price:{Convert(dis_stock_p)}    Current Share Price: {Convert(c_share_p)}"
                f"\n{ticker_str} is undervalued by {Convert(val_percent)}%")
    else:
        out += (f"\nTarget Price: {Convert(dis_stock_p)}    Current Share Price: {Convert(c_share_p)}"
                f"\n{ticker_str} is overvalued by {Convert(-val_percent)}%")
    out += f"   WACC = {Convert(100 * wacc_2)}%"
    return out, fcf  # Output string + projected FCFs (current + all projected years)


def FMajor(ticker_str, proj_time_0, growth_r_0, p_growth_r_0, wacc_1):
    t = yf.Ticker(ticker_str)
    print("Accessing balance sheet, income & cash flow statements from Yahoo Finance.")
    b_sheet = t.balance_sheet.T.fillna(0)
    c_flow = t.cashflow.T.fillna(0)
    i_state = t.incomestmt.T.fillna(0)

    # Safely pull values with fallbacks for financial companies
    ebit_0 = get_val(i_state, ["EBIT", "Operating Income"])
    ebitda_0 = get_val(i_state, ["EBITDA", "Normalized EBITDA", "Operating Income"])
    cap_ex_0 = get_val(c_flow, ['Capital Expenditure'])
    tax_0 = get_val(i_state, ['Tax Provision'])

    # Safely pull series for Non-Cash Working Capital
    tca = get_series(b_sheet, ['Total Current Assets'])
    cash = get_series(b_sheet, ['Cash And Cash Equivalents'])
    sti = get_series(b_sheet, ['Other Short Term Investments'])
    tcl = get_series(b_sheet, ['Total Current Liabilities'])
    cdcl = get_series(b_sheet, ['Current Debt And Capital Lease Obligation'])
    cd = get_series(b_sheet, ['Current Debt'])

    ncwc = (tca - cash - sti) - (tcl - cdcl - cd)

    # Check history length to avoid crashing on companies with < 2 years of data
    ncwc_1 = float(ncwc.iloc[1]) if len(ncwc) > 1 else float(ncwc.iloc[0])
    ncwc_0 = float(ncwc.iloc[0])

    stock_p_0 = float(t.history(period="1d")['Close'].iloc[0])
    total_cash_0 = float(t.info.get('totalCash', 0))
    total_debt_0 = float(t.info.get('totalDebt', 0))
    s_out_0 = float(t.info.get('sharesOutstanding', 1))

    dcf_string, proj_fcf_list = DCF(proj_time_0, growth_r_0, p_growth_r_0, wacc_1, ebit_0,
                                    ebitda_0, ncwc_1, ncwc_0, cap_ex_0, tax_0, stock_p_0,
                                    s_out_0, total_cash_0, total_debt_0, ticker_str)

    past_fcf_series = get_series(c_flow, ['Free Cash Flow'])  # Historical FCFs
    return dcf_string, proj_fcf_list, past_fcf_series


# ----------------------------------------------------------------------------
# Pygame widgets
# ----------------------------------------------------------------------------
def draw_text(text, font, x, y):  # Draws text, one line per \n
    line_h = font.get_linesize()
    for i, line in enumerate(text.split('\n')):
        screen.blit(font.render(line, 1, TEXT), (x, y + i * line_h))


def draw_button(rect, label, fill, border, text_col, font_size=15):  # Filled, outlined, centred-label button
    pygame.draw.rect(screen, fill, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)
    surf = pygame.font.SysFont(FONT, font_size).render(label, True, text_col)
    screen.blit(surf, surf.get_rect(center=rect.center))


def inp_box(x, y, w, h, text, font_size=15):  # Input box: accent border on hover, label drawn top-left
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, TAG, rect, border_radius=8)
    border = ACCENT if rect.collidepoint(pygame.mouse.get_pos()) else BORDER
    pygame.draw.rect(screen, border, rect, 2, border_radius=8)
    draw_text(text, pygame.font.SysFont(FONT, font_size), x + 8, y + 8)
    return rect


def ui(screen_, mainClock):
    global screen
    screen = screen_
    placeholders = ["Ticker", "Projection Time", "Growth Rate", "Perpetuity Growth Rate",
                    "Enter WACC or Leave Empty", "Press to Output"]
    text = placeholders.copy()
    active_box = None

    view_mode = 'dcf'  # Active tab: 'dcf' or 'risk'
    risk_ticker = "Ticker"
    risk_active = False  # Whether the risk ticker box is being edited
    risk_data = None
    risk_surf = None

    graph_surf = None  # Stock chart surface
    fcf_graph_surf = None
    wacc_open = False  # Whether the WACC checkbox is ticked
    wacc_anim = 0.0  # 0 = checkbox only, 1 = input fully expanded

    anim_full_text = ""  # Output-text letter-by-letter reveal
    anim_text_idx = 0
    stock_ticker = ""
    stock_data = None  # (dates, values)
    stock_n = 0
    fcf_data = None  # (past_series, proj_list)
    fcf_n = 0
    fcf_n_float = 0.0
    fcf_total = 0

    def wacc_box():  # Row-2 checkbox; ticking it animates the WACC input out to fill the column
        nonlocal wacc_anim
        x, y = COL_X[0], row_y(2)
        full_w = COL_X[1] + BOX_W - x  # Expanded width reaches the right edge of the 2nd column above
        target = 1.0 if wacc_open else 0.0
        wacc_anim = min(target, wacc_anim + 0.08) if wacc_anim < target else max(target, wacc_anim - 0.08)
        eased = 1 - (1 - wacc_anim) ** 3  # Ease-out cubic
        cb_w = BOX_W // 4  # Checkbox stays fixed; the input slides out from it
        rect = pygame.Rect(x, y, cb_w + int((full_w - cb_w) * eased), BOX_H)
        pygame.draw.rect(screen, TAG, rect, border_radius=8)
        border = ACCENT if rect.collidepoint(pygame.mouse.get_pos()) else BORDER
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)
        if wacc_anim > 0.02:  # Divider appears once the input begins sliding out
            pygame.draw.line(screen, BORDER, (x + cb_w, y + 2), (x + cb_w, y + BOX_H - 2), 2)
        if wacc_open:  # Accent square as the visual tick
            pygame.draw.rect(screen, ACCENT, pygame.Rect(x + 12, y + 12, cb_w - 24, BOX_H - 24), border_radius=4)
        if wacc_anim >= 0.99:  # Render WACC text only once fully expanded so it isn't clipped
            draw_text(text[4], pygame.font.SysFont(FONT, 15), x + cb_w + 8, y + 8)
        return rect

    def DCFOutput():  # Runs the DCF and kicks off the reveal animation
        nonlocal graph_surf, fcf_graph_surf, anim_full_text, anim_text_idx
        nonlocal stock_data, fcf_data, stock_ticker, stock_n, fcf_n, fcf_n_float, fcf_total
        try:
            wacc_val = WACC(text[0]) if text[4] == placeholders[4] else float(text[4]) / 100
            out_ans, proj_fcf_list, past_fcf_series = FMajor(text[0].upper(), text[1], text[2], text[3], wacc_val)
            try:
                hist = yf.Ticker(text[0].upper()).history(period="5y")['Close']
                stock_data = (list(hist.index), list(hist.values)) if not hist.empty else None
            except:
                stock_data = None
            fcf_data = (past_fcf_series, proj_fcf_list)
            stock_ticker = text[0].upper()
            stock_n = fcf_n = 0
            fcf_n_float = 0.0
            past_len = len(past_fcf_series) if past_fcf_series is not None and not past_fcf_series.empty else 0
            fcf_total = past_len + (len(proj_fcf_list) if proj_fcf_list else 0)
            graph_surf = fcf_graph_surf = None
            anim_full_text = out_ans  # Begin the letter-by-letter reveal
            anim_text_idx = 0
            text[5] = ""
        except:  # Invalid input should never crash the program
            text[5] = "Invalid Input"
            graph_surf = fcf_graph_surf = stock_data = fcf_data = None

    def RiskOutput():  # Computes and stores the risk profile for the entered ticker
        nonlocal risk_data, risk_surf
        try:
            risk_data = RiskData(risk_ticker.upper())
            risk_surf = risk_graph(risk_data["returns"], 412, 300)
        except:  # Sentinel "error" drives the Invalid Input message in draw_risk_view
            risk_data, risk_surf = "error", None

    def draw_tabs():  # Centred top-middle tab bar with a rule beneath; returns {mode: rect}
        rects = {}
        for (label, mode), x in zip([("DCF Analysis", 'dcf'), ("Risk Profile", 'risk')], TAB_X):
            r = pygame.Rect(x, TABS_Y, TAB_W, TAB_H)
            active = view_mode == mode
            draw_button(r, label, TAG if active else BG, ACCENT if active else BORDER,
                        TEXT if active else MUTED)
            rects[mode] = r
        pygame.draw.line(screen, BORDER, (0, TABS_RULE_Y), (SCREEN_W, TABS_RULE_Y), 1)  # Tab-bar rule
        return rects

    def draw_beta_gauge(x, y, w, d):  # 0..2 beta bar with a market (1.0) marker
        beta = d['beta'] if d['beta'] is not None else d['ann_vol'] / 0.2
        pygame.draw.rect(screen, BORDER, pygame.Rect(x, y, w, 16), border_radius=8)
        col = GREEN if beta < 0.8 else AMBER if beta <= 1.2 else ACCENT
        frac = max(0.0, min(1.0, beta / 2.0))
        if frac > 0:
            pygame.draw.rect(screen, col, pygame.Rect(x, y, max(8, int(w * frac)), 16), border_radius=8)
        mx = x + w // 2  # Market reference at beta = 1.0
        pygame.draw.line(screen, TEXT, (mx, y - 4), (mx, y + 20), 2)
        cap = pygame.font.SysFont(FONT, 13).render("Beta vs Market  (1.0 = moves with the market)", True, MUTED)
        screen.blit(cap, (x, y + 24))

    def draw_dcf_view():  # Animates + draws the DCF tab; returns the input-box rects
        nonlocal anim_text_idx, graph_surf, fcf_graph_surf, stock_n, fcf_n, fcf_n_float
        pygame.draw.line(screen, BORDER, (490, TABS_RULE_Y), (490, SCREEN_H), 1)  # Quadrant dividers
        pygame.draw.line(screen, BORDER, (0, 400), (SCREEN_W, 400), 1)

        if anim_text_idx < len(anim_full_text):  # Reveal the output text first
            anim_text_idx = min(len(anim_full_text), anim_text_idx + 8)
            text[5] = anim_full_text[:anim_text_idx]
        elif anim_full_text:  # Then animate the graphs
            if stock_data and stock_n < len(stock_data[0]):
                stock_n = min(len(stock_data[0]), stock_n + max(1, len(stock_data[0]) // 30))
                graph_surf = stock_graph(stock_ticker, stock_data[0], stock_data[1], stock_n, 412, 342)
            if fcf_data and fcf_n < fcf_total:
                fcf_n_float += 0.5
                if int(fcf_n_float) > fcf_n:
                    fcf_n = min(fcf_total, int(fcf_n_float))
                    fcf_graph_surf = fcf_graph(fcf_data[0], fcf_data[1], fcf_n, 412, 342)

        out_font = pygame.font.SysFont(FONT, 15)  # Output box sizes to its visible text
        out_lines = (text[5] or " ").split('\n')
        out_w = max(max((out_font.size(l)[0] for l in out_lines), default=0) + 16, 60)
        out_h = max(len(out_lines) * out_font.get_linesize() + 16, 30)

        rects = [inp_box(COL_X[0], row_y(0), BOX_W, BOX_H, text[0]),
                 inp_box(COL_X[1], row_y(0), BOX_W, BOX_H, text[1]),
                 inp_box(COL_X[0], row_y(1), BOX_W, BOX_H, text[2]),
                 inp_box(COL_X[1], row_y(1), BOX_W, BOX_H, text[3]),
                 wacc_box(),  # Row 2, column 0
                 inp_box(COL_X[0], row_y(3), out_w, out_h, text[5])]  # Row 3 output box

        label = f"{stock_ticker} : Stock Performance" if stock_ticker else "Stock Performance"
        static_graph_box(520, 50, 420, 350, label, graph_surf)
        static_graph_box(520, 420, 420, 350, "Free Cash Flow : Past & Projected", fcf_graph_surf)
        return rects

    def draw_risk_view():  # Draws the Risk Profile tab; returns (input rect, button rect)
        ti_rect = inp_box(COL_X[0], row_y(0), BOX_W, BOX_H, risk_ticker)
        btn_rect = pygame.Rect(COL_X[1], row_y(0), BOX_W, BOX_H)
        border = ACCENT if btn_rect.collidepoint(pygame.mouse.get_pos()) else BORDER
        draw_button(btn_rect, "Analyse Risk", TAG, border, TEXT)

        if isinstance(risk_data, dict):
            d = risk_data
            beta_str = f"{d['beta']:.2f}" if d['beta'] is not None else "N/A (volatility-implied)"
            lines = [d['name'], "",
                     f"Beta: {beta_str}",
                     f"Annualised Volatility: {d['ann_vol'] * 100:.2f}%",
                     f"1Y Return: {d['ann_ret'] * 100:.2f}%",
                     f"Max Drawdown: {d['max_dd'] * 100:.2f}%",
                     f"Sharpe Ratio: {d['sharpe']:.2f}",
                     f"Risk-Free Rate: {d['rf'] * 100:.2f}%", "",
                     f"Risk Profile: {d['category']}"]
            draw_text("\n".join(lines), pygame.font.SysFont(FONT, 16), 50, 150)
            draw_beta_gauge(50, 430, 400, d)
            if risk_surf is not None:
                screen.blit(risk_surf, (524, 150))
        else:
            msg = "Invalid Input" if risk_data == "error" else "Enter a ticker and click Analyse Risk"
            draw_text(msg, pygame.font.SysFont(FONT, 16), 50, 150)
        return ti_rect, btn_rect

    def static_graph_box(x, y, w, h, label, surf):  # Graph surface, or a centred placeholder label
        rect = pygame.Rect(x, y, w, h)
        if surf is not None:
            screen.blit(surf, (x + 4, y + 4))
        else:
            s = pygame.font.SysFont(FONT, 16).render(label, True, TEXT)
            screen.blit(s, s.get_rect(center=rect.center).topleft)
        return rect

    while True:
        screen.fill(BG)
        tab_rects = draw_tabs()
        rect, risk_input_rect, risk_btn_rect = [], None, None
        if view_mode == 'dcf':
            rect = draw_dcf_view()
        else:
            risk_input_rect, risk_btn_rect = draw_risk_view()

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

            if event.type == MOUSEBUTTONDOWN:
                switched = False  # Tab clicks take priority
                for mode, tr in tab_rects.items():
                    if tr.collidepoint(event.pos):
                        view_mode, active_box, risk_active, switched = mode, None, False, True

                if not switched and view_mode == 'dcf':
                    for i in range(len(rect)):
                        if rect[i].collidepoint(event.pos):
                            active_box = i
                            if i == 5:
                                DCFOutput()
                            elif i == 4:  # WACC widget: left 1/4 is the checkbox, right 3/4 the input
                                if event.pos[0] < COL_X[0] + BOX_W // 4:
                                    wacc_open = not wacc_open
                                    if not wacc_open:
                                        text[i] = placeholders[i]  # Back to auto WACC
                                    active_box = None
                                elif wacc_open:  # Clear so the user can type
                                    text[i] = ""
                                else:
                                    active_box = None
                            else:
                                text[i] = ""
                elif not switched and view_mode == 'risk':
                    if risk_input_rect and risk_input_rect.collidepoint(event.pos):
                        risk_active, risk_ticker = True, ""
                    elif risk_btn_rect and risk_btn_rect.collidepoint(event.pos):
                        risk_active = False
                        RiskOutput()
                    else:
                        risk_active = False

            if event.type == KEYDOWN:
                if view_mode == 'dcf' and active_box is not None:
                    if event.key == K_RETURN:
                        DCFOutput()
                    elif active_box != 5:
                        if event.key == K_BACKSPACE:
                            text[active_box] = text[active_box][:-1]
                        else:
                            text[active_box] += event.unicode
                elif view_mode == 'risk' and risk_active:
                    if event.key == K_RETURN:
                        risk_active = False
                        RiskOutput()
                    elif event.key == K_BACKSPACE:
                        risk_ticker = risk_ticker[:-1]
                    else:
                        risk_ticker += event.unicode

            if view_mode == 'dcf':  # Restore placeholders for empty, unfocused boxes
                for j in range(len(rect)):
                    if active_box != j and text[j] == "":
                        text[j] = placeholders[j]
            elif not risk_active and risk_ticker == "":
                risk_ticker = "Ticker"

        pygame.display.update()
        mainClock.tick(30)


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
screen = None
if __name__ == "__main__":
    pygame.init()
    pygame.display.set_caption("DCF | Modelling Tool")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))  # Inputs on the left, graphs stacked on the right
    ui(screen, pygame.time.Clock())