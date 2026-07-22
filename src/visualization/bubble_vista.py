import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

df = pd.read_csv('input/trial.csv')

def parse_and_standardize_size(size_str):
    if pd.isna(size_str):
        return np.nan, np.nan, np.nan

    parts = str(size_str).strip().split()
    if len(parts) < 2:
        return np.nan, np.nan, np.nan

    try:
        raw_value = float(parts[0])
        raw_unit = parts[1].upper()
    except:
        return np.nan, np.nan, np.nan

    unit_to_mb = {
        'KB': 1 / 1024,
        'MB': 1,
        'GB': 1024,
        'TB': 1024 * 1024,
    }

    if raw_unit not in unit_to_mb:
        return np.nan, np.nan, np.nan

    standardized_mb = raw_value * unit_to_mb[raw_unit]
    return raw_value, raw_unit, standardized_mb


parsed_size = df['Size'].apply(parse_and_standardize_size)
df[['SizeValue', 'SizeUnit', 'SizeMB']] = pd.DataFrame(parsed_size.tolist(), index=df.index)
df['OriginalSize'] = df['SizeValue'].round(2).astype(str) + ' ' + df['SizeUnit'].astype(str)
df = df.dropna(subset=['SizeMB', 'Domain'])

size_log = np.log10(df['SizeMB'].clip(lower=1e-9))
log_min = size_log.min()
log_max = size_log.max()
if log_max > log_min:
    df['BubbleSize'] = 14 + (size_log - log_min) / (log_max - log_min) * 56
else:
    df['BubbleSize'] = 30

# Sort domains by mean size
domain_order = (
    df.groupby('Domain')['SizeMB']
    .mean()
    .sort_values()
    .index
    .tolist()
)

if 'Generic' in domain_order:
    domain_order = [d for d in domain_order if d != 'Generic'] + ['Generic']

df['Domain'] = pd.Categorical(df['Domain'], categories=domain_order, ordered=True)

colors = ['#4C78A8', '#72B7B2', '#54A24B', '#EECA3B', '#B279A2', '#9D755D', '#BAB0AC']
domain_colors = {d: colors[i % len(colors)] for i, d in enumerate(domain_order)}

fig = go.Figure()


def build_grouped_labels(domain_df, threshold_mb):
    ordered = domain_df.sort_values('SizeMB').copy()
    ordered['GroupedLabel'] = ''

    current_indices = []
    current_items = []
    current_anchor = None

    for idx, row in ordered.iterrows():
        size_mb = row['SizeMB']
        name = row['Dataset Name']

        if not current_indices:
            current_indices = [idx]
            current_items = [(name, size_mb)]
            current_anchor = size_mb
            continue

        if abs(size_mb - current_anchor) <= threshold_mb:
            current_indices.append(idx)
            current_items.append((name, size_mb))
        else:
            sorted_names = [item[0] for item in sorted(current_items, key=lambda item: item[1], reverse=True)]
            ordered.loc[current_indices[0], 'GroupedLabel'] = '<br>'.join(sorted_names)
            current_indices = [idx]
            current_items = [(name, size_mb)]
            current_anchor = size_mb

    if current_indices:
        sorted_names = [item[0] for item in sorted(current_items, key=lambda item: item[1], reverse=True)]
        ordered.loc[current_indices[0], 'GroupedLabel'] = '<br>'.join(sorted_names)

    return ordered[['GroupedLabel']]


def get_label_group_threshold(domain_name):
    domain_key = str(domain_name).strip().lower()
    if domain_key == 'manufacturing':
        return 900
    if domain_key == 'healthcare':
        return 50
    return 800


def build_label_positions(domain_df, proximity_log_threshold=0.03):
    ordered = domain_df.sort_values('SizeMB').copy()
    ordered['LabelPosition'] = 'middle right'

    labeled = ordered[ordered['GroupedLabel'].astype(str).str.len() > 0]
    last_log_size = None
    alternate = False

    for idx, row in labeled.iterrows():
        current_log_size = np.log10(max(row['SizeMB'], 1e-9))

        if last_log_size is not None and abs(current_log_size - last_log_size) <= proximity_log_threshold:
            ordered.loc[idx, 'LabelPosition'] = 'top right' if not alternate else 'bottom right'
            alternate = not alternate
        else:
            ordered.loc[idx, 'LabelPosition'] = 'middle right'
            alternate = False

        last_log_size = current_log_size

    return ordered[['LabelPosition']]


for domain in domain_order:
    domain_mask = df['Domain'] == domain
    if domain == 'Generic':
        df.loc[domain_mask, 'GroupedLabel'] = df.loc[domain_mask, 'Dataset Name']
    elif str(domain).strip().lower() == 'healthcare':
        healthcare_df = df[domain_mask]
        in_range_mask = (healthcare_df['SizeMB'] >= 10**3) & (healthcare_df['SizeMB'] <= 10**4) | (healthcare_df['SizeMB'] >= 50**7) & (healthcare_df['SizeMB'] <= 10**8)

        in_range_df = healthcare_df[in_range_mask].sort_values('SizeMB', ascending=False)
        if not in_range_df.empty:
            grouped_text = '<br>'.join(in_range_df['Dataset Name'].tolist())
            first_idx = in_range_df.index[0]
            df.loc[first_idx, 'GroupedLabel'] = grouped_text
            if len(in_range_df.index) > 1:
                df.loc[in_range_df.index[1:], 'GroupedLabel'] = ''

        out_of_range_index = healthcare_df[~in_range_mask].index
        df.loc[out_of_range_index, 'GroupedLabel'] = df.loc[out_of_range_index, 'Dataset Name']
    else:
        grouped_labels = build_grouped_labels(
            df[domain_mask],
            threshold_mb=get_label_group_threshold(domain)
        )
        df.loc[grouped_labels.index, 'GroupedLabel'] = grouped_labels['GroupedLabel']
    label_positions = build_label_positions(df[domain_mask])
    df.loc[label_positions.index, 'LabelPosition'] = label_positions['LabelPosition']

# Ensure CT-RATE label is never dropped by grouping logic
empty_grouped_label_mask = df['GroupedLabel'].astype(str).str.strip() == ''


for domain in domain_order:
    ddf = df[df['Domain'] == domain]
    display_text = ddf['GroupedLabel'].copy()
    ignore_ct_rate_mask = (
        ddf['Dataset Name'].astype(str).str.contains('CT-RATE', case=False, na=False)
        | display_text.astype(str).str.contains('CT-RATE', case=False, na=False)
    )
    display_text = display_text.mask(ignore_ct_rate_mask, '')

    fig.add_trace(go.Scatter(
        x=[domain] * len(ddf),
        y=ddf['SizeMB'],
        mode='markers+text',
        marker=dict(
            size=ddf['BubbleSize'],
            color=domain_colors[domain],
            line=dict(width=1, color='black'),
            opacity=0.75
        ),
        text=display_text,
        textposition=ddf['LabelPosition'],
        textfont=dict(size=10, color='black'),
        hovertext=(
            "<b>" + ddf['Dataset Name'] + "</b><br>"
            "Domain: " + ddf['Domain'].astype(str) + "<br>"
            "Original Size: " + ddf['OriginalSize'].astype(str) + "<br>"
            "Standardized Size: " + ddf['SizeMB'].round(2).astype(str) + " MB<br>"
            "Sub-Domain: " + ddf['Sub-Domain'].astype(str)
        ),
        hovertemplate='%{hovertext}<extra></extra>',
        name=domain
    ))

min_exp = int(np.floor(np.log10(df['SizeMB'].min())))
max_exp = int(np.ceil(np.log10(df['SizeMB'].max())))
y_tick_vals = [10 ** exp for exp in range(min_exp, max_exp + 1)]
y_tick_text = [f"10<sup>{exp}</sup>" for exp in range(min_exp, max_exp + 1)]

domain_guide_lines = [
    dict(
        type='line',
        xref='x',
        yref='paper',
        x0=domain,
        x1=domain,
        y0=0,
        y1=1,
        line=dict(color='rgba(120, 120, 120, 0.25)', width=1)
    )
    for domain in domain_order
]

y_guide_lines = [
    dict(
        type='line',
        xref='paper',
        yref='y',
        x0=0,
        x1=1,
        y0=tick,
        y1=tick,
        line=dict(color='rgba(120, 120, 120, 0.20)', width=1)
    )
    for tick in y_tick_vals
]

fig.update_layout(
    title=None,
    xaxis=dict(
        title='Domain',
        categoryorder='array',
        categoryarray=domain_order,
        range=[-0.5, len(domain_order) - 0.25],
        tickangle=0,
        automargin=True,
        showline=True,
        linecolor='black',
        linewidth=1,
        mirror=True
    ),
    yaxis=dict(
        title='Standardized Size (MB)',
        type='log',
        tickmode='array',
        tickvals=y_tick_vals,
        ticktext=y_tick_text,
        tickfont=dict(size=12),
        showline=True,
        linecolor='black',
        linewidth=1,
        mirror=True
    ),
    shapes=domain_guide_lines + y_guide_lines,
    plot_bgcolor='white',
    paper_bgcolor='white',
    width=950,
    height=650,
    legend=dict(
        title='Domain',
        orientation='h',
        x=0.5,
        y=1.15,
        xanchor='center',
        yanchor='bottom'
    ),
    margin=dict(t=10, b=20, r=20)
)

output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(output_dir, exist_ok=True)



png_path = os.path.join(output_dir, 'vista_bubble.png')
fig.write_image(png_path)

pdf_path = os.path.join(output_dir, 'vista_bubble.pdf')
fig.write_image(pdf_path)
