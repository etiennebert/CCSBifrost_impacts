
clc, clear
% put the number of your GLORIA version
gloria_vrs = 59;


%% setwd
% hard drive location for GLORIA
wd.hd = ['D:\GLORIA_MRIOS_' num2str(gloria_vrs)];
wd.hd_strs = fullfile(wd.hd, 'stressor');

VA = {'VA_Taxes_Production','VA_Subsidies_Production','VA_Net_Surplus'};

%% create the helper to sum among countries

h = zeros(984, 6);  % 984 rows, 6 columns
% Define indices for each column in a single step
for k = 1:6
    h(k:6:end, k) = 1;  % Increment by 6, starting from k
end

%% looping over the years

for Year = 2023:2024
    

    Year = 2024;
    tic
    % Define the base and target directories
    baseDir = wd.hd;
    targetDir = fullfile(baseDir, sprintf("GLORIA_MRIOs_%d_%d", gloria_vrs, Year));

    searchPattern = sprintf("*_120secMother_AllCountries_002_V-Results_%d_0%d_Markup001(full).csv", Year, gloria_vrs);

    files = dir(fullfile(targetDir, searchPattern));

    % Check if there are any files that match the pattern
    if isempty(files.name)
        error('No files found matching pattern: %s', searchPattern);
    else  
        % Import data from the selected file
        V = importdata(fullfile(files.folder,files.name));
    end

    r = (V' * h)';
    
  %%
    
  r_test = r(4,:)'; 
    
  r_test_c = sum(r_test(37441:37680),"all")
  
  
  for i = 1:3
        
        data = r(i+1,:);
        Year_st = string(Year);
        filename = ['CQ_T_' VA{i} '_' num2str(Year) '.mat'];

        % Construct the full file path
        fullFilePath = fullfile(wd.hd_strs, filename);
    
        % Save the variable 's' at the constructed file path
        save(fullFilePath, 'data');
        toc;
    end

end
