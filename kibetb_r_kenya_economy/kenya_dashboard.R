# =============================================================================
#  Kenya's Economy, 2000-2025: A Statistical Dashboard in ggplot2
#  Data: World Bank, World Development Indicators (downloaded Oct 2026)
#  Run:  Rscript kenya_dashboard.R      -> output/kenya_economy_dashboard.png
# =============================================================================
suppressPackageStartupMessages({
  library(ggplot2); library(dplyr); library(tidyr); library(scales); library(patchwork)
})

# --------------------------------------------------------------------------- data
# Optional: refresh from the World Bank API (needs the WDI package + internet)
REFRESH <- FALSE
if (REFRESH && requireNamespace("WDI", quietly = TRUE)) {
  ind <- c(gdp_growth_pct = "NY.GDP.MKTP.KD.ZG", inflation_cpi_pct = "FP.CPI.TOTL.ZG",
           kes_per_usd = "PA.NUS.FCRF", gdp_per_capita_usd = "NY.GDP.PCAP.CD",
           agriculture_share_gdp_pct = "NV.AGR.TOTL.ZS",
           remittances_share_gdp_pct = "BX.TRF.PWKR.DT.GD.ZS")
  WDI::WDI(country = "KE", indicator = ind, start = 2000, end = 2025) |>
    select(year, all_of(names(ind))) |> arrange(year) |>
    write.csv("data/kenya_wdi_2000_2025.csv", row.names = FALSE)
}
ke <- read.csv("data/kenya_wdi_2000_2025.csv")

# --------------------------------------------------------------------------- theme
ink <- "#1d2433"; muted <- "#6b7280"; grid <- "#e6e8ec"
green <- "#1f7a5a"; red <- "#b8412f"; gold <- "#c9922e"; blue <- "#2a5d8f"

theme_dash <- function() {
  theme_minimal(base_size = 11, base_family = "sans") +
    theme(plot.title = element_text(face = "bold", size = 12.5, colour = ink),
          plot.subtitle = element_text(size = 9.5, colour = muted, margin = margin(b = 8)),
          plot.caption = element_text(size = 8, colour = muted, hjust = 0),
          axis.text = element_text(colour = muted, size = 8.5),
          axis.title = element_text(colour = muted, size = 8.5),
          panel.grid.minor = element_blank(),
          panel.grid.major = element_line(colour = grid, linewidth = .35),
          panel.grid.major.x = element_blank(),
          legend.position = "none",
          plot.margin = margin(10, 14, 10, 10),
          plot.background = element_rect(fill = "white", colour = NA))
}
yrs <- scale_x_continuous(breaks = seq(2000, 2025, 5), expand = expansion(mult = .02))

# --------------------------------------------------------------------------- KPI strip
kpi <- function(value, label, sub, col = ink) {
  ggplot() + xlim(0, 1) + ylim(0, 1) + theme_void() +
    annotate("text", x = 0.04, y = .70, label = value, hjust = 0, size = 8.5, fontface = "bold", colour = col) +
    annotate("text", x = 0.04, y = .33, label = label, hjust = 0, size = 3.5, colour = ink, fontface = "bold") +
    annotate("text", x = 0.04, y = .12, label = sub, hjust = 0, size = 3, colour = muted) +
    theme(plot.background = element_rect(fill = "#f6f7f9", colour = NA),
          plot.margin = margin(4, 6, 4, 6))
}
last <- ke |> filter(year == max(year)); first <- ke |> filter(year == min(year))
n_yrs <- last$year - first$year
cagr <- (last$gdp_per_capita_usd / first$gdp_per_capita_usd)^(1 / n_yrs) - 1
avg_g <- mean(ke$gdp_growth_pct)
k1 <- kpi(sprintf("%.1f%%", avg_g), "Average real GDP growth",
          sprintf("%d-%d, %d of %d years above 3%%", first$year, last$year,
                  sum(ke$gdp_growth_pct > 3), nrow(ke)), green)
k2 <- kpi(dollar(round(last$gdp_per_capita_usd)), sprintf("GDP per capita, %d", last$year),
          sprintf("%.1fx since %d (%.1f%% a year, current US$)",
                  last$gdp_per_capita_usd / first$gdp_per_capita_usd, first$year, 100 * cagr), blue)
k3 <- kpi(sprintf("%.1f%%", last$inflation_cpi_pct), sprintf("CPI inflation, %d", last$year),
          sprintf("Peak: %.1f%% in %d", max(ke$inflation_cpi_pct),
                  ke$year[which.max(ke$inflation_cpi_pct)]), gold)
k4 <- kpi(sprintf("KES %.0f", last$kes_per_usd), sprintf("Per US dollar, %d average", last$year),
          sprintf("Shilling lost %.0f%% of its value vs %d",
                  100 * (1 - first$kes_per_usd / last$kes_per_usd), first$year), red)

# --------------------------------------------------------------------------- A. growth
p_growth <- ke |>
  mutate(dir = gdp_growth_pct >= avg_g) |>
  ggplot(aes(year, gdp_growth_pct)) +
  geom_hline(yintercept = 0, colour = ink, linewidth = .4) +
  geom_hline(yintercept = avg_g, linetype = "22", colour = muted, linewidth = .4) +
  geom_col(aes(fill = dir), width = .72) +
  geom_smooth(method = "loess", span = .6, se = FALSE, formula = y ~ x,
              colour = ink, linewidth = .7) +
  annotate("text", x = 2008, y = -1.1, label = "2008\npost-election crisis\n+ global recession",
           size = 2.6, colour = red, lineheight = .9) +
  annotate("text", x = 2020, y = -1.6, label = "2020\nCOVID-19", size = 2.6, colour = red, lineheight = .9) +
  annotate("text", x = 2000.3, y = avg_g + .45, label = sprintf("25-yr avg %.1f%%", avg_g),
           hjust = 0, size = 2.7, colour = muted) +
  scale_fill_manual(values = c(`TRUE` = green, `FALSE` = "#9cc5b4")) +
  scale_y_continuous(labels = label_percent(scale = 1), limits = c(-2.6, 9)) + yrs +
  labs(title = "Resilient growth, punctuated by shocks",
       subtitle = "Real GDP growth, % per year. Dark bars beat the long-run average; line is a LOESS-smoothed trend",
       x = NULL, y = NULL) + theme_dash()

# --------------------------------------------------------------------------- B. inflation vs target band
p_infl <- ke |>
  ggplot(aes(year, inflation_cpi_pct)) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = 2.5, ymax = 7.5, fill = green, alpha = .09) +
  annotate("text", x = 2024.8, y = 2.9, label = "CBK target range: 5% +/- 2.5 pp", hjust = 1, size = 2.6, colour = green) +
  geom_line(colour = gold, linewidth = .9) +
  geom_point(aes(colour = inflation_cpi_pct > 7.5), size = 2) +
  geom_text(data = \(d) d |> slice_max(inflation_cpi_pct, n = 3),
            aes(label = sprintf("%.0f%%", inflation_cpi_pct)), vjust = -.9, size = 2.7, colour = red) +
  scale_colour_manual(values = c(`TRUE` = red, `FALSE` = gold)) +
  scale_y_continuous(labels = label_percent(scale = 1), limits = c(0, 29)) + yrs +
  labs(title = "Inflation has been tamed since the early 2010s",
       subtitle = "Consumer price inflation, % per year. Red points sit above the target range",
       x = NULL, y = NULL) + theme_dash()

# --------------------------------------------------------------------------- C. exchange rate
fx_lab <- ke |> filter(year %in% c(2000, 2015, 2023, 2025))
p_fx <- ke |>
  ggplot(aes(year, kes_per_usd)) +
  geom_area(fill = red, alpha = .10) +
  geom_line(colour = red, linewidth = .9) +
  geom_point(data = fx_lab, colour = red, size = 2) +
  geom_text(data = fx_lab, aes(label = sprintf("%.0f", kes_per_usd)), vjust = -1, size = 2.8, colour = ink) +
  annotate("text", x = 2023, y = 152, label = "2023 peak, then\npartial recovery",
           size = 2.6, colour = muted, lineheight = .9) +
  scale_y_continuous(limits = c(0, 160), expand = expansion(mult = c(0, .02))) + yrs +
  labs(title = "A steadily weaker shilling",
       subtitle = "Official exchange rate, Kenyan shillings per US dollar (annual average)",
       x = NULL, y = NULL) + theme_dash()

# --------------------------------------------------------------------------- D. per-capita income with log-linear fit
fit <- lm(log(gdp_per_capita_usd) ~ year, data = ke)
growth_rate <- exp(coef(fit)[["year"]]) - 1
p_pc <- ke |>
  ggplot(aes(year, gdp_per_capita_usd)) +
  geom_line(aes(y = exp(predict(fit))), linetype = "22", colour = muted) +
  geom_line(colour = blue, linewidth = 1) +
  geom_point(colour = blue, size = 1.6) +
  annotate("text", x = 2001, y = 2200, hjust = 0, size = 2.8, colour = muted,
           label = sprintf("Log-linear trend: +%.1f%% a year\nR-squared = %.2f",
                           100 * growth_rate, summary(fit)$r.squared)) +
  annotate("text", x = 2013.4, y = 2300, label = "2014 GDP\nrebasing", size = 2.6, colour = muted, lineheight = .9) +
  scale_y_continuous(labels = label_dollar(), limits = c(0, 3100)) + yrs +
  labs(title = "Average income has grown more than fivefold",
       subtitle = "GDP per capita, current US$. Dashed line: exponential trend fitted by OLS on log values",
       x = NULL, y = NULL) + theme_dash()

# --------------------------------------------------------------------------- E. growth-inflation path
p_path <- ke |>
  ggplot(aes(inflation_cpi_pct, gdp_growth_pct)) +
  annotate("rect", xmin = 2.5, xmax = 7.5, ymin = -Inf, ymax = Inf, fill = green, alpha = .07) +
  geom_path(aes(colour = year), linewidth = .45, alpha = .8, arrow = arrow(length = unit(.12, "cm"), type = "closed")) +
  geom_point(aes(colour = year), size = 2.2) +
  geom_text(data = \(d) d |> filter(year %in% c(2000, 2008, 2011, 2020, 2021, 2025)),
            aes(label = year), size = 2.6, vjust = -1, colour = ink) +
  scale_colour_gradient(low = "#c6d4e3", high = ink) +
  scale_x_continuous(labels = label_percent(scale = 1)) +
  scale_y_continuous(labels = label_percent(scale = 1)) +
  labs(title = "From volatile to stable: the growth-inflation path",
       subtitle = "Each point is a year (darker = more recent). Recent years cluster in the target band with ~5% growth",
       x = "CPI inflation", y = "Real GDP growth") + theme_dash() +
  theme(panel.grid.major.x = element_line(colour = grid, linewidth = .35))

# --------------------------------------------------------------------------- F. structural shift
struct <- ke |>
  select(year, Agriculture = agriculture_share_gdp_pct, Remittances = remittances_share_gdp_pct) |>
  pivot_longer(-year, names_to = "series", values_to = "share")
p_struct <- struct |>
  ggplot(aes(year, share, colour = series)) +
  geom_line(linewidth = .9) +
  geom_point(data = \(d) d |> filter(year %in% c(2000, 2025)), size = 2) +
  geom_text(data = \(d) d |> filter(year == 2025),
            aes(label = sprintf("%s\n%.1f%%", series, share)), hjust = -.12, size = 2.7, lineheight = .9) +
  scale_colour_manual(values = c(Agriculture = green, Remittances = gold)) +
  scale_y_continuous(labels = label_percent(scale = 1), limits = c(0, 30)) +
  scale_x_continuous(breaks = seq(2000, 2025, 5), limits = c(2000, 2030.5)) +
  labs(title = "Farming still a fifth of GDP; diaspora money rising",
       subtitle = "Agriculture value added and personal remittances received, % of GDP",
       x = NULL, y = NULL) + theme_dash()

# --------------------------------------------------------------------------- assemble
kpis <- (k1 | k2 | k3 | k4)
body <- (p_growth | p_infl) / (p_fx | p_pc) / (p_path | p_struct)
dash <- (kpis / body) + plot_layout(heights = c(.42, 3.3)) +
  plot_annotation(
    title = "Kenya's Economy, 2000-2025",
    subtitle = "Twenty-five years of growth, price stability and currency pressure, from World Bank World Development Indicators",
    caption = paste("Source: World Bank WDI (NY.GDP.MKTP.KD.ZG, FP.CPI.TOTL.ZG, PA.NUS.FCRF, NY.GDP.PCAP.CD,",
                    "NV.AGR.TOTL.ZS, BX.TRF.PWKR.DT.GD.ZS). Built in R with ggplot2 + patchwork."),
    theme = theme(plot.title = element_text(face = "bold", size = 22, colour = ink),
                  plot.subtitle = element_text(size = 11.5, colour = muted, margin = margin(b = 10)),
                  plot.caption = element_text(size = 8.5, colour = muted, hjust = 0),
                  plot.margin = margin(18, 18, 12, 18),
                  plot.background = element_rect(fill = "white", colour = NA)))

dir.create("output", showWarnings = FALSE)
ggsave("output/kenya_economy_dashboard.png", dash, width = 15, height = 17, dpi = 170, bg = "white")
ggsave("output/kenya_economy_dashboard.pdf", dash, width = 15, height = 17, bg = "white")

# --------------------------------------------------------------------------- stats summary
cat("\n== Summary statistics ==\n")
print(summary(ke[, -1]))
cat(sprintf("\nCorrelation growth vs inflation: r = %.2f (p = %.3f)\n",
            cor(ke$gdp_growth_pct, ke$inflation_cpi_pct),
            cor.test(ke$gdp_growth_pct, ke$inflation_cpi_pct)$p.value))
cat(sprintf("Inflation SD 2000-2012: %.1f pp | 2013-2025: %.1f pp\n",
            sd(ke$inflation_cpi_pct[ke$year <= 2012]), sd(ke$inflation_cpi_pct[ke$year > 2012])))
cat(sprintf("Per-capita income log-linear growth: %.2f%%/yr (R2 = %.3f)\n",
            100 * growth_rate, summary(fit)$r.squared))
