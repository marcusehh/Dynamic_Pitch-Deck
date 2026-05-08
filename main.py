import io
import yfinance as yf #Imports Yahoo Finance
import pandas as pd # Imports pandas for working with tabular data
import pygame, sys
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter #Used to format FCF y-axis ticks with the Convert() helper
from matplotlib.dates import YearLocator, DateFormatter #Used to lock the stock-graph x-axis to year ticks only
from pygame.locals import *

def out_graph_surf(ticker_str,w,h):
    try:
        stock = yf.Ticker(ticker_str)
        hist = stock.history(period="5y")['Close']

        if hist.empty:
            raise ValueError("No data")

        fig, ax = plt.subplots(figsize=(w/100,h/100),dpi=100)
        fig.patch.set_facecolor('#0a0a0a') #Matches site --bg
        ax.set_facecolor('#0a0a0a') #Matplotlib uses decimals between 0 & 1 rather than 0 to 256 (now using site --bg hex directly)
        ax.plot(hist.index, hist.values,color='#a1a1aa',linewidth=1.0) #Site --text-muted grey (kept from the projection iteration)

        ax.set_title(f"{ticker_str.upper()} : Stock Performance",color='#f4f4f5') #Site --text
        ax.xaxis.set_major_locator(YearLocator()) #Show only one tick per year
        ax.xaxis.set_major_formatter(DateFormatter('%Y')) #Render that tick as the bare year (no months)
        ax.tick_params(axis='x', colors='#a1a1aa') #Site --text-muted
        ax.tick_params(axis='y', colors='#a1a1aa') #Site --text-muted
        ax.spines['bottom'].set_color('#27272a') #Site --border
        ax.spines['left'].set_color('#27272a') #Site --border
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        buf = io.BytesIO() #Saves the graph as a png, to a buffer
        fig.savefig(buf, format='png')
        buf.seek(0)

        surf = pygame.image.load(buf)
        plt.close(fig)
        return surf

    except:
        return None

def out_graph_surf_anim(ticker_str, dates, values, proj_dates, proj_values, n, w, h): #Same as out_graph_surf but plots past (grey) and a linear projected line to the target price (red) with axes locked to the full range
    try:
        if not dates:
            raise ValueError("No data")
        proj_dates = proj_dates or []
        proj_values = proj_values or []
        total = len(dates) + len(proj_dates)
        n = max(0, min(n, total))
        n_past = min(n, len(dates))
        n_proj = max(0, n - len(dates))
        fig, ax = plt.subplots(figsize=(w/100,h/100),dpi=100)
        fig.patch.set_facecolor('#0a0a0a')
        ax.set_facecolor('#0a0a0a')
        if n_past > 0:
            ax.plot(dates[:n_past], values[:n_past], color='#a1a1aa', linewidth=1.0) #Past performance: site --text-muted grey
        if n_proj > 0:
            xs = [dates[-1]] + list(proj_dates[:n_proj]) #Stitch the projection onto the last past point so the line is continuous
            ys = [values[-1]] + list(proj_values[:n_proj])
            ax.plot(xs, ys, color='#c0392b', linewidth=1.0) #Projected line to target: site --accent red
        x_max = proj_dates[-1] if proj_dates else dates[-1]
        ax.set_xlim(dates[0], x_max) #Lock axes to full historical + projected range so the line draws into a fixed canvas
        all_y = list(values) + list(proj_values)
        y_min = min(all_y); y_max = max(all_y)
        y_pad = (y_max - y_min) * 0.05 if y_max > y_min else 1
        ax.set_ylim(y_min - y_pad, y_max + y_pad)
        ax.set_title(f"{ticker_str.upper()} : Stock Performance",color='#f4f4f5')
        ax.xaxis.set_major_locator(YearLocator()) #Show only one tick per year
        ax.xaxis.set_major_formatter(DateFormatter('%Y')) #Render that tick as the bare year (no months)
        ax.tick_params(axis='x', colors='#a1a1aa')
        ax.tick_params(axis='y', colors='#a1a1aa')
        ax.spines['bottom'].set_color('#27272a')
        ax.spines['left'].set_color('#27272a')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        surf = pygame.image.load(buf)
        plt.close(fig)
        return surf
    except:
        return None

def out_fcf_graph_surf(past_fcf_series, proj_fcf, w, h): #Builds a graph of past and projected FCFs
    try:
        if (past_fcf_series is None or past_fcf_series.empty) and (not proj_fcf):
            raise ValueError("No data") #If neither past nor projected data exists, raise error

        fig, ax = plt.subplots(figsize=(w/100, h/100), dpi=100)
        fig.patch.set_facecolor('#0a0a0a') #Matches site --bg
        ax.set_facecolor('#0a0a0a') #Matplotlib uses decimals between 0 & 1 rather than 0 to 256 (now using site --bg hex directly)

        last_year = None
        if past_fcf_series is not None and not past_fcf_series.empty:
            past_pairs = sorted([(d.year, float(v)) for d, v in past_fcf_series.items()]) #Sorts past FCFs by year ascending
            past_years = [p[0] for p in past_pairs]
            past_values = [p[1] for p in past_pairs]
            ax.plot(past_years, past_values, color='#a1a1aa', linewidth=1.4, marker='o', label='Past FCF') #Plots past FCFs (site --text-muted)
            last_year = past_years[-1]

        if proj_fcf:
            if last_year is None:
                from datetime import datetime
                last_year = datetime.now().year #Falls back to current year if no past data
            proj_years = [last_year + i for i in range(len(proj_fcf))] #Generates year labels for each projected FCF
            ax.plot(proj_years, proj_fcf, color='#c0392b', linewidth=1.4, marker='o', linestyle='--', label='Projected FCF') #Plots projected FCFs (site --accent)

        ax.set_title("Free Cash Flow : Past & Projected", color='#f4f4f5') #Site --text
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: Convert(v))) #Replaces the 1e11 offset with human-readable units (million/billion/trillion)
        ax.tick_params(axis='x', colors='#a1a1aa') #Site --text-muted
        ax.tick_params(axis='y', colors='#a1a1aa') #Site --text-muted
        ax.spines['bottom'].set_color('#27272a') #Site --border
        ax.spines['left'].set_color('#27272a') #Site --border
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        leg = ax.legend(facecolor='#18181b', edgecolor='#27272a') #Site --tag-bg / --border for the legend chrome
        for txt in leg.get_texts():
            txt.set_color('#f4f4f5') #Site --text
        fig.tight_layout()

        buf = io.BytesIO() #Saves the graph as a png, to a buffer
        fig.savefig(buf, format='png')
        buf.seek(0)

        surf = pygame.image.load(buf)
        plt.close(fig)
        return surf

    except:
        return None

def out_fcf_graph_surf_anim(past_fcf_series, proj_fcf, n, w, h): #Same as out_fcf_graph_surf but plots only the first n points (past first, then projected) with axes locked to the full range
    try:
        past_pairs = []
        if past_fcf_series is not None and not past_fcf_series.empty:
            past_pairs = sorted([(d.year, float(v)) for d, v in past_fcf_series.items()])
        last_year = past_pairs[-1][0] if past_pairs else None
        if last_year is None:
            from datetime import datetime
            last_year = datetime.now().year #Falls back to current year if no past data
        proj_pairs = [(last_year + i, float(v)) for i, v in enumerate(proj_fcf or [])]
        all_pairs = past_pairs + proj_pairs
        if not all_pairs:
            raise ValueError("No data")
        n = max(0, min(n, len(all_pairs)))
        n_past = min(n, len(past_pairs))
        n_proj = max(0, n - len(past_pairs))
        fig, ax = plt.subplots(figsize=(w/100, h/100), dpi=100)
        fig.patch.set_facecolor('#0a0a0a')
        ax.set_facecolor('#0a0a0a')
        if n_past > 0:
            ax.plot([p[0] for p in past_pairs[:n_past]], [p[1] for p in past_pairs[:n_past]], color='#a1a1aa', linewidth=1.4, marker='o', label='Past FCF')
        if n_proj > 0:
            ax.plot([p[0] for p in proj_pairs[:n_proj]], [p[1] for p in proj_pairs[:n_proj]], color='#c0392b', linewidth=1.4, marker='o', linestyle='--', label='Projected FCF')
        all_xs = [p[0] for p in all_pairs]; all_ys = [p[1] for p in all_pairs]
        ax.set_xlim(min(all_xs) - 0.5, max(all_xs) + 0.5) #Lock axes to full range so points pop in against a fixed frame
        y_min, y_max = min(all_ys), max(all_ys)
        y_pad = (y_max - y_min) * 0.05 if y_max > y_min else 1
        ax.set_ylim(y_min - y_pad, y_max + y_pad)
        ax.set_title("Free Cash Flow : Past & Projected", color='#f4f4f5')
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: Convert(v)))
        ax.tick_params(axis='x', colors='#a1a1aa')
        ax.tick_params(axis='y', colors='#a1a1aa')
        ax.spines['bottom'].set_color('#27272a')
        ax.spines['left'].set_color('#27272a')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if n_past > 0 or n_proj > 0:
            try:
                leg = ax.legend(facecolor='#18181b', edgecolor='#27272a')
                for txt in leg.get_texts():
                    txt.set_color('#f4f4f5')
            except:
                pass
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        surf = pygame.image.load(buf)
        plt.close(fig)
        return surf
    except:
        return None

def inp_box (screen,x,y,w,h,text,font_size=15): #Builds a UI input box

    inp_rect = pygame.Rect(x,y,w,h) #Takes an input to draw a rectangle of the given position, x & y as well as, width and height
    pygame.draw.rect(screen,(24,24,27),inp_rect,border_radius=8) #Draws the rectangle with the colour gray (now site --tag-bg #18181b with 8px radius from --radius)

    out_colour = (192,57,43) if inp_rect.collidepoint(pygame.mouse.get_pos()) else (39,39,42) #If the mouse is touching the button, its outline will be white (now site --accent on hover, --border at rest)
    pygame.draw.rect(screen,out_colour,inp_rect,2,border_radius=8) #The outline is 3px (slimmed to 2px to match the site's restrained borders)

    draw_text(text, pygame.font.SysFont("inter,segoeui,consolas",font_size),x+8,y+8)  # Draw text on the input_box (Inter primary, Segoe UI / Consolas fallback)
    return inp_rect #Returns the rectangle UI element
def ui (screen,mainClock):
    saved_Text_Data = ["Ticker","Projection Time","Growth Rate","Perpetuity Growth Rate","Enter WACC or Leave Empty","Press to Output"] #List for text inputs
    text = saved_Text_Data.copy()
    active_box = None #Initialises the active_box

    graph_surf = None #Updates graph surface #Graph
    fcf_graph_surf = None #Tracks the FCF (past + projected) graph surface
    wacc_open = False #Whether the WACC checkbox is ticked
    wacc_anim = 0.0 #Animation progress for the input expansion: 0 = checkbox only, 1 = fully expanded
    #Output text reveal animation (graphs no longer auto-animate; user clicks each graph's title button to fold them out)
    anim_phase = 'idle'
    anim_full_text = ""
    anim_text_idx = 0
    #Per-graph fold-out state (mirrors wacc_open / wacc_anim) - title button by default, click to fold out the full graph
    stock_open = False
    stock_anim = 0.0
    fcf_open = False
    fcf_anim = 0.0

    def wacc_box(): #Checkbox-only by default; when ticked, the WACC input animates out to the right
        nonlocal wacc_anim
        #Step the animation toward the current target each frame (reaches the endpoint in ~0.4s at 30fps)
        target = 1.0 if wacc_open else 0.0
        if wacc_anim < target:
            wacc_anim = min(target, wacc_anim + 0.08)
        elif wacc_anim > target:
            wacc_anim = max(target, wacc_anim - 0.08)
        #Eased progress so the slide feels less linear (ease-out cubic)
        eased = 1 - (1 - wacc_anim) ** 3
        cb_w = 62 #Checkbox width (1/4 of the 250-wide fully-expanded box)
        total_w = cb_w + int(188 * eased) #Right-3/4 width grows with the animation
        full_rect = pygame.Rect(50,190,total_w,50)
        pygame.draw.rect(screen,(24,24,27),full_rect,border_radius=8) #Same fill as inp_box (site --tag-bg)
        out_colour = (192,57,43) if full_rect.collidepoint(pygame.mouse.get_pos()) else (39,39,42) #Site --accent on hover, --border at rest
        pygame.draw.rect(screen,out_colour,full_rect,2,border_radius=8)
        if wacc_anim > 0.02: #Vertical divider only visible once the input has begun to slide out
            pygame.draw.line(screen,(39,39,42),(50+cb_w,192),(50+cb_w,238),2)
        if wacc_open: #When ticked, fill the checkbox area with an accent square as the visual tick
            tick_rect = pygame.Rect(50+12,190+12,cb_w-24,50-24)
            pygame.draw.rect(screen,(192,57,43),tick_rect,border_radius=4)
        if wacc_anim >= 0.99: #Render WACC text only once the input is fully expanded (so it's not clipped mid-slide)
            draw_text(text[4],pygame.font.SysFont("inter,segoeui,consolas",15),50+cb_w+8,198)
        return full_rect

    def DCFOutput():
        nonlocal graph_surf #Updates the variable #Graph
        nonlocal fcf_graph_surf #Updates the FCF graph variable
        nonlocal anim_phase, anim_full_text, anim_text_idx
        try:
            pygame.display.update()
            if (text[4] == "Enter WACC or Leave Empty"):  # If the user enters a WACC, the program will not calculate one itself
                wacc_val = WACC(text[0])
            else:
                wacc_val = float(text[4])/100
            out_ans, proj_fcf_list, past_fcf_series = FMajor(text[0].upper(), text[1], text[2], text[3], wacc_val)
            text[5] = out_ans

            graph_surf = out_graph_surf(text[0],412,342) #Outputs a graph based on the ticker based on stock performance #Graph (rendered slightly smaller than the 420x350 fold-out box so the container border stays visible)
            fcf_graph_surf = out_fcf_graph_surf(past_fcf_series, proj_fcf_list, 412, 342) #Outputs FCF graph for past and projected free cash flows (also inset 4px so the box frames it)
            #Start the letter-by-letter reveal of the DCF text (graphs are revealed by clicking their fold-out buttons)
            anim_full_text = out_ans
            anim_text_idx = 0
            text[5] = ""
            anim_phase = 'text'
        except:  # If there are invalid inputs, then the program will not crash
            pygame.display.update()
            text[5] = "Invalid Input"
            graph_surf = None #Graph
            fcf_graph_surf = None #Resets the FCF graph on invalid input
            anim_phase = 'idle'

    def graph_fold_box(x, y, btn_w, btn_h, full_w, full_h, label, is_open, anim, surf): #Fold-out tile: title button by default; click to expand to the full graph (returns the current rect and the next anim value)
        target = 1.0 if is_open else 0.0
        if anim < target: anim = min(target, anim + 0.08) #Same step as wacc_anim so timing matches
        elif anim > target: anim = max(target, anim - 0.08)
        eased = 1 - (1 - anim) ** 3 #Ease-out cubic, same curve as wacc_box
        cur_w = btn_w + int((full_w - btn_w) * eased)
        cur_h = btn_h + int((full_h - btn_h) * eased)
        rect = pygame.Rect(x, y, cur_w, cur_h)
        pygame.draw.rect(screen, (24,24,27), rect, border_radius=8) #Site --tag-bg
        if anim >= 0.99 and surf is not None: #Once fully expanded, blit the pre-rendered graph inset 4px so the box frames it
            screen.blit(surf, (x+4, y+4))
        elif anim < 0.99: #While collapsed or mid-animation, show the title centred in the box
            label_font = pygame.font.SysFont("inter,segoeui,consolas", 16)
            label_surf = label_font.render(label, True, (244,244,245))
            label_rect = label_surf.get_rect(center=rect.center)
            screen.blit(label_surf, label_rect.topleft)
        out_colour = (192,57,43) if rect.collidepoint(pygame.mouse.get_pos()) else (39,39,42) #Site --accent on hover, --border at rest (drawn last so it stays visible on top of the graph)
        pygame.draw.rect(screen, out_colour, rect, 2, border_radius=8)
        return rect, anim


    while True: #This code will always run
        screen.fill((10,10,10)) #Makes the screen black (now site --bg #0a0a0a)

        #Quadrant dividers (site --border #27272a) - vertical at the window midpoint, horizontal at the window midpoint
        pygame.draw.line(screen,(39,39,42),(490,0),(490,800),1)
        pygame.draw.line(screen,(39,39,42),(0,400),(980,400),1)

        #Animation tick: only the output text reveals automatically. Each graph waits for its title button to be clicked.
        if anim_text_idx < len(anim_full_text):
            anim_text_idx = min(len(anim_full_text), anim_text_idx + 8) #~8 chars per frame
            text[5] = anim_full_text[:anim_text_idx]

        #Dynamic output box: width and height fit only the currently-visible characters
        out_font = pygame.font.SysFont("inter,segoeui,consolas", 15)
        out_lines = (text[5] or " ").split('\n')
        out_max_w = max((out_font.size(line)[0] for line in out_lines), default=0)
        out_box_w = max(out_max_w + 16, 60)
        out_box_h = max(len(out_lines) * out_font.get_linesize() + 16, 30)

        rect = [inp_box(screen,50,50,200,50,text[0]),
                inp_box(screen,270,50,200,50,text[1]),
                inp_box(screen,50,120,200,50,text[2]),
                inp_box(screen,270,120,200,50,text[3]),
                wacc_box(), #WACC widget: left 1/4 is the checkbox, right 3/4 is the input (editable only when ticked)
                inp_box(screen,50,260,out_box_w,out_box_h,text[5],font_size=15)] #Initalises all squares (output box now sizes to its current text content)

        #Graph fold-out tiles: each is a title button by default; click to expand into the full pre-rendered graph
        stock_label = (f"{text[0].upper()} : Stock Performance" if text[0] and text[0] != saved_Text_Data[0] else "Stock Performance")
        stock_rect, stock_anim = graph_fold_box(520, 50, 260, 50, 420, 350, stock_label, stock_open, stock_anim, graph_surf)
        fcf_rect, fcf_anim = graph_fold_box(520, 420, 320, 50, 420, 350, "Free Cash Flow : Past & Projected", fcf_open, fcf_anim, fcf_graph_surf)


        for event in pygame.event.get():
            if event.type == QUIT:  #Closes the program if the user clicks the X
                pygame.quit()
                sys.exit()

            if event.type == MOUSEBUTTONDOWN: #Checks whether anything has been inputted
                #Graph fold-out buttons: click to toggle each graph open/closed (independent of the input rect[] list)
                if stock_rect.collidepoint(event.pos):
                    stock_open = not stock_open
                elif fcf_rect.collidepoint(event.pos):
                    fcf_open = not fcf_open
                for i in range(len(rect)):
                    if (rect[i].collidepoint(event.pos)):  #Active is validated if the mouse/clicker touching the input button
                        active_box = i
                        if (i==5): #Outputs results
                            DCFOutput()
                        elif (i==4): #WACC widget: differentiate between left-1/4 checkbox click and right-3/4 input click
                            if event.pos[0] < 50 + 62: #Click in the left 1/4 toggles the tick
                                wacc_open = not wacc_open
                                if not wacc_open:
                                    text[i] = saved_Text_Data[i] #Restore placeholder so the DCF uses auto WACC again
                                active_box = None #Checkbox click should not make the input editable
                            elif wacc_open: #Right-3/4 click while ticked: clear so user can type
                                text[i] = ""
                            else: #Right-3/4 click while unticked: non-interactive
                                active_box = None
                        else:
                            text[i] = ""

            if event.type == KEYDOWN and active_box is not None:  # If a key is being inputted
                if event.key == K_RETURN: #If the user clicks the "enter" key
                    DCFOutput() #Outputs results : Duplicated
                elif (active_box != 5):
                    if event.key == K_BACKSPACE:
                        text[active_box] = text[active_box][:-1] #Removes the last character
                    else:
                        text[active_box] += event.unicode #Adds the character inputted

            for j in range(len(rect)):
                if ((active_box != j) and (text[j] == "")):
                    text[j] = saved_Text_Data[j]

        pygame.display.update()
        mainClock.tick(30)
def draw_text (text,font,x,y): #No clue mate, ACC for drawing text at this location
    textobj = font.render(text,1,(244,244,245)) #Site --text #f4f4f5
    textrect = textobj.get_rect()
    textrect.topleft = (x,y)
    screen.blit(textobj,textrect)
#Actual Content -->
def Convert(uncoverted_num): #Function to round and convert huge numbers to more understandable formats
    num_abs = abs(uncoverted_num) #Removes direction, only keeps magnitude
    if num_abs < 1000000:
        return (f"{(uncoverted_num):.2f}")
    elif num_abs < 1000000000:
        return(f"{(uncoverted_num/1000000):.2f} million")
    elif num_abs < 1000000000000:
        return(f"{(uncoverted_num/1000000000):.2f} billion")
    else:
        return(f"{(uncoverted_num/1000000000000):.2f} trillion")
def WACC(ticker_str): #Automatically creates a WACC

    ticker_wacc = yf.Ticker(ticker_str) #Saves the ticker as a local variable for the WACC function

    i_state = ticker_wacc.incomestmt  #Saves income statement
    i_state = i_state.T.fillna(0)  # Saves the income statement as a table & replaces NaN with 0
    equ_val_wacc = ticker_wacc.info.get("marketCap",0) #Saves market cap
    total_debt = ticker_wacc.info.get("totalDebt",0) #Saves total debt
    weight_of_equ = equ_val_wacc/(total_debt + equ_val_wacc) #Saves the weight of equity
    risk_free_r = (yf.Ticker("^TNX")).history(period='1d')['Close'].iloc[0] / 100 #Saves risk-free rate (10 year US treasury yield)
    cost_of_equ = risk_free_r + (0.05 * ticker_wacc.info.get("beta",1.0)) #Adds risk-free rate to beta multiplied by market risk premium (assumed to be 0.05)
    weight_of_debt = total_debt/(total_debt + equ_val_wacc) #Saves the weight of debt
    cost_of_debt = abs(i_state.get('Interest Expense',0).iloc[0])/total_debt #Retrieves magnitude of interest expense (as it is sometimes reported negative) and divides it by total debt
    tax_r = i_state.get('Tax Provision').iloc[0] / i_state.get('Pretax Income').iloc[0] #Calculates tax rate by dividing tax provision by pre-tax income
    wacc = weight_of_equ * cost_of_equ + weight_of_debt * cost_of_debt * (1-tax_r) #(Percent of Equity/Weight of Equity x Cost of Equity) + (Percent of debt/Weight of debt x Cost of debt x (1 - tax rate))

    return(wacc)
def DCF(proj_time_1,growth_r_1,p_growth_r_1,wacc_2,ebit_1, ebitda_1, ncwc_1_a, ncwc_1_b, cap_ex_1, tax_1, c_share_p, s_out_1, total_cash_1, total_debt_1, ticker_str):

    mega_string =""
    #Initialises lists
    cap_ex_2 = [cap_ex_1]
    ebit_2 = [ebit_1]
    ebitda_2 = [ebitda_1]
    tax_2 = [tax_1]

    ncwc_b = [ncwc_1_b]
    ncwc_c = []

    fcf = []

    d_a = [(ebitda_2[0] - ebit_2[0])] #Initialised depreciation & amortization

    # Makes statistics the correct format
    growth_r_1 = float(growth_r_1)/100
    p_growth_r_1 = float(p_growth_r_1)/100
    present_value = []

    #Calculates NCWC change from this year to last
    ncwc_c.append(ncwc_b[0] - ncwc_1_a)

    fcf.append(ebit_2[0] - tax_2[0] + cap_ex_2[0] - ncwc_c[0] + d_a[0]) #Calculates current FCF
    present_value.append(fcf[0])

    for i in range(1, int(proj_time_1) + 1): #Calculates all future FCFs for the given projection period
        ebit_2.append(ebit_2[i - 1] * (1 + growth_r_1))

        ncwc_b.append((ncwc_b[i-1] / ebit_2[i-1]) * ebit_2[i]) #Calculates the ncwc balance for the given year
        ncwc_c.append(ncwc_b[i] - ncwc_b[i-1]) #Calculates the year-on-year change in ncwc
        d_a.append(d_a[i - 1] * (1 + growth_r_1))
        cap_ex_2.append(cap_ex_2[i-1]* (1 + growth_r_1))
        tax_2.append((tax_2[0] / ebit_2[0]) * ebit_2[i])

        fcf.append(ebit_2[i] - tax_2[i] + cap_ex_2[i] - ncwc_c[i] + d_a[i]) #Free cash flow calculation
        present_value.append(fcf[i]/((1+wacc_2)**i)) # Calculates present value using discount factor


    term_value = (fcf[int(proj_time_1)]*(1+p_growth_r_1))/(wacc_2-p_growth_r_1) #Calculates terminal value
    ent_val = (term_value/(1+wacc_2)**int(proj_time_1)) + sum(present_value[1:]) #Calculates projected enterprise value

    equ_val = ent_val + total_cash_1 - total_debt_1 #Calculates equity value

    dis_stock_p = equ_val/s_out_1
    mega_string += (f"Terminal Value: {Convert(term_value)}\nImplied Enterprise Value: {Convert(ent_val)}\nImplied Equity Value: {Convert(equ_val)}   ")

    val_percent = (dis_stock_p-c_share_p)/c_share_p*100 #Calcuates the percentage under/overvaluation between current and target stock price

    if dis_stock_p > c_share_p:
        mega_string += (f"\nTarget Price:{Convert(dis_stock_p)}    Current Share Price: {Convert(c_share_p)}\n{ticker_str} is undervalued by {Convert(val_percent)}%")
    else:
        mega_string += (f"\nTarget Price: {Convert(dis_stock_p)}    Current Share Price: {Convert(c_share_p)}\n{ticker_str} is overvalued by {Convert(-val_percent)}%")

    mega_string += f"   WACC = {Convert(100*wacc_2)}%"

    return (mega_string, fcf) #Returns the answers and the projected FCF list (current year + all projected years)
def FMajor(ticker_str,proj_time_0,growth_r_0,p_growth_r_0,wacc_1):
    ticker_2 = yf.Ticker(ticker_str)  # Defines the stock
    print("Accessing balance sheet, income & cash flow statements from Yahoo Finance.")  # Notifies the user the progress of the calculations

    b_sheet = ticker_2.balance_sheet  # aves the balance sheet
    b_sheet = b_sheet.T.fillna(0)  #Saves the balance sheet as a table & replaces NaN with 0
    c_flow = ticker_2.cashflow  #Saves cash flow statement
    c_flow = c_flow.T.fillna(0)  #Saves the cash flow statement as a table & replaces NaN with 0
    i_state = ticker_2.incomestmt  #Saves income statement
    i_state = i_state.T.fillna(0)  #Saves the income statement as a table & replaces NaN with 0

    ebit_0 = i_state.get("EBIT") #Retrieves EBIT
    ebitda_0 = i_state.get("EBITDA") #Retrieves EBITDA
    cap_ex_0 = c_flow.get('Capital Expenditure') #Retrieves capex
    tax_0 = i_state.get('Tax Provision') #Retrieves tax provision

    ncwc = ((b_sheet.get('Total Current Assets', 0) - b_sheet.get('Cash And Cash Equivalents', 0) -
             b_sheet.get('Other Short Term Investments', 0)) - (b_sheet.get('Total Current Liabilities', 0) -
             b_sheet.get('Current Debt And Capital Lease Obligation',0) -
             b_sheet.get('Current Debt',0)))  # Non-cash working capital calculation

    stock_p_0 = (ticker_2.history(period="1d"))['Close'] #Retrieves stock price by checking the most recent closing price
    total_cash_0 = (ticker_2.info).get('totalCash',0) #Retrieves total cash
    total_debt_0 = (ticker_2.info).get('totalDebt',0) #Retrieves total debt
    s_out_0 = ticker_2.info.get('sharesOutstanding',0) #Retrieves the number of outstanding shares
    #If there is missing elements from balance sheet of three items above, they will be automatically set to 0

    dcf_string, proj_fcf_list = DCF(proj_time_0,growth_r_0,p_growth_r_0,wacc_1,ebit_0.iloc[0], ebitda_0.iloc[0], ncwc.iloc[1], ncwc.iloc[0], cap_ex_0.iloc[0], tax_0.iloc[0], stock_p_0.iloc[0],s_out_0, total_cash_0, total_debt_0,ticker_str)  # Calls the DCF
    past_fcf_series = c_flow.get('Free Cash Flow') #Retrieves historical free cash flows from cash flow statement
    return dcf_string, proj_fcf_list, past_fcf_series #Returns DCF output, projected FCFs, and historical FCFs
# <-- Actual Content

#GUI Code
pygame.init()
pygame.display.set_caption("DCF | Modelling Tool")
screen = pygame.display.set_mode((980, 800)) #Wider window: inputs on the left, both graphs stacked on the right side
mainClock = pygame.time.Clock()

ui(screen,mainClock)

"""
results = ui(screen,mainClock)

proj_time_str = results[1]
growth_r_str = results[2]
p_growth_r_str = results[3]
wacc_0 = results[4]
if wacc_0 == "WACC":
wacc_0 = WACC() #Saves the WACC
else:
    wacc_0 = float(wacc_0)

#Main Code
ticker_str = input("Enter ticker:") #Input ticker - Is string global variable to be used in output of DCF
proj_time_str = input("Enter projection time: ")
growth_r_str = input("Enter Growth Rate: ") #Input Growth Rate
p_growth_r_str = input("Enter Perpetuity Growth Rate: ") # Input P Growth Rate
wacc_0 = WACC() #Calls WACC function to enable the user to either manually or automatically have a WACC used for the DCF


FMajor(ticker_str,proj_time_str,growth_r_str,p_growth_r_str,wacc_0) #Calls the major function, with DCF inside
"""
