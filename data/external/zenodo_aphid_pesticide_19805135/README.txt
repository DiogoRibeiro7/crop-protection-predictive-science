Overview
This dataset contains five worksheets, each corresponding to a separate experiment investigating the combined effects of heat stress and pesticide exposure on aphid survival under controlled and field conditions.

Sheet 1 (Experiment 1) examines the effects of varying pesticide concentrations and heat exposure on aphid survival.
Sheet 2 (Experiment 2) focuses on the interaction between heat intensity and pesticide application and their joint impact on aphid mortality.
Sheet 3 (Experiment 3) evaluates how the duration of heat exposure and the order of heat and pesticide treatments influence aphid survival.
Sheet 4 (Experiment 4) investigates the effects of different time intervals between heat exposure and pesticide application.
Sheet 5 (Experiment 5) presents field trial data used to assess model performance under real agricultural conditions.

1. Experiment 1

This sheet contains four variables describing the effects of pesticide concentration and temperature on aphid survival.

Variable	Description
Temperature: Treatment temperature (°C) at which aphids were exposed during the experiment.
CONC: Pesticide concentration applied in each treatment.
TOTAL: Total number of aphids recorded before treatment (initial population size).
DEAD: Number of aphids that died after treatment, used to assess mortality under different temperature and pesticide conditions.

2. Experiment 2

This sheet contains five variables describing the combined effects of heat intensity, pesticide concentration, and exposure duration on aphid mortality:

Variable	Description
Temperature: Treatment temperature (°C) representing the intensity of heat exposure applied to aphids.
CONC: Pesticide concentration used in each treatment.
Treatment_Time: Duration (e.g., hours or minutes) for which aphids were exposed to the specified temperature.
TOTAL: Total number of aphids recorded before treatment (initial population size).
DEAD: Number of aphids that died after treatment, used to quantify mortality under different combinations of heat intensity, pesticide concentration, and exposure duration.

3. Experiment 3

This sheet contains seven variables describing the effects of heat exposure duration and the sequence of heat and pesticide application on aphid survival.

Variable	Description
Temperature: Treatment temperature (°C) at which aphids were exposed.
CONC: Pesticide concentration applied in each treatment.
Treatment_Time: Duration of heat exposure (min) to which aphids were subjected.
Interval: Time interval (h) between heat exposure and pesticide application.
Order: Order of treatments, indicating whether pesticide was applied before or after heat exposure (i.e., pre_pesticide or post_pesticide).
TOTAL: Total number of aphids recorded before treatment (initial population size).
DEAD: Number of aphids that died after treatment, used to assess mortality under different treatment sequences and conditions.

4. Experiment 4

This sheet contains six variables describing the effects of different time intervals between heat exposure and pesticide application on aphid survival.

Variable	Description
Temperature: Treatment temperature (°C) at which aphids were exposed.
CONC: Pesticide concentration applied in each treatment.
Treatment_Time: Duration of heat exposure (min) applied to aphids.
Interval: Time interval (h) between heat exposure and pesticide application.
TOTAL: Total number of aphids recorded before treatment (initial population size).
DEAD: Number of aphids that died after treatment, used to quantify mortality under different timing intervals between heat and pesticide exposure.

5. Experiment 5

This sheet contains field trial data used to evaluate model performance under real agricultural conditions.

Variable	Description
Site: Experimental location, including Langfang and Xinxiang.
Treat: Treatment group based on pesticide application timing (A, B, C).
Replicate: Replicate identifier for each treatment.
SamplingDay: Sampling time after pesticide application, indicating whether observations were conducted at 3 days (day3_postpesticide) or 7 days (day7_postpesticide).
Date: Calendar date of sampling.
Base_number: Initial aphid population size before treatment.
PopSize: Aphid population size observed after treatment.
Order: Sequence of heat and pesticide exposure.
Interval: Time interval between heat exposure and pesticide application.
Type: Environmental condition during treatment, classified as Hot (heat stress conditions) or Normal (ambient temperature conditions).
DH_above26: Heat dose calculated as cumulative degree-hours above 26°C.
Mortality: Observed aphid mortality rate following treatment.
CONC: Pesticide concentration applied in the field.















