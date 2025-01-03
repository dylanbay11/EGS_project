library(tidyverse)
library(naniar)
bigdf <- read_csv(file = "~/Desktop/dshw/pypractice/df_joined.csv")
colnames(bigdf)[1] <- "index"
bigdf <- select(bigdf, c("index", "Name", "orig_price", "Start", "End"), everything())
bigdf
gg_miss_var(bigdf, show_pct = TRUE)
colnames(bigdf)
vis_miss(bigdf)
nadf <- filter(bigdf, is.na(orig_price))

withmiss <- read_csv(file = "~/Desktop/dshw/EGS_project/df_complete.csv")
gg_miss_var(withmiss, show_pct = TRUE)
