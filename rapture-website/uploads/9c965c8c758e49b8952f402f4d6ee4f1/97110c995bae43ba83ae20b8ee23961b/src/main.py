import smile

experiment_id = smile.get_experiment_id()
smile.log(f"This is experiment {experiment_id}, reporting!", name1="Justin", name2="Nick")