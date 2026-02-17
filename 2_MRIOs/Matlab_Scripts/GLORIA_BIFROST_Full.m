%% Creation of the database

clc, clear

% Constants and Parameters
gloria_vrs = 59;

year = 2021;

stressor = {'ghg_ar6','VA_Net_Surplus','VA_Subsidies_Production','VA_Taxes_Production','employment_skill_high','employment_skill_middle','employment_skill_low'};
% ,

nbr_sectors_ixp = 240;
segment = (nbr_sectors_ixp/2)-1;

%%
% Define paths
wd.hd = ['D:\GLORIA_MRIOS_' num2str(gloria_vrs)];
wd.hd_ma = fullfile(wd.hd, 'matrix calc');
wd.hd_strs = fullfile(wd.hd, 'stressor');
y.bifrost = ['C:\Users\etber\OneDrive - Massachusetts Institute of Technology\Documents\CCS\4. Costs\']
wd.hd_sa = ['C:\Users\etber\OneDrive - Massachusetts Institute of Technology\Documents\CCS\5. MRIOs\']

Y_cty = importdata(fullfile(y.bifrost,'2_BIFROST_Input_Vektor.csv'));
Y_cty = Y_cty /1000; % GLORIA is in '000 of USD

%%

% label = readcell(fullfile(y.bifrost,'2_BIFROST_Input_Vektor_Label.csv'), 'Delimiter', ';')';
% label = label(:,5);
% newColumnName = {'Full_ID'};
% labelTable = cell2table(label, 'VariableNames', newColumnName);
% 
% nRows = height(labelTable);  % Total number of rows in the original table
% numRepeats = 39360;          % Number of times each row should be repeated
% repIndices = repelem(1:nRows, numRepeats);  % Generate repetition indices
% 
% Full_ID_Table = labelTable(repIndices, :);
% 
% numRepeats = 39360; % Number of times each row should be repeated
% nRows = height(labelTable); % Total number of rows in the original table
% repID = repmat((1:39360)', 252, 1); % Repeat each index numRepeats times
% newColumnName = {'Number_ID'};
% Number_ID_Table = array2table(repID, 'VariableNames', newColumnName);
% 
% BIFROST_ID = [Full_ID_Table, Number_ID_Table];
% 
% writetable(BIFROST_ID, 'C:\Users\etber\OneDrive - Danmarks Tekniske Universitet\Dokumenter\DTU_BIFROST\BIFROST\5. MRIOs\4. Output\ID_label.csv');
% 
% clearvars BIFROST_ID Full_ID_Tables Full_ID_Table Number_ID_Table repID 

%%
    % Load data
    L = loadMatrix(wd.hd_ma, 'L', year);
   
    %%
    x = loadMatrix(wd.hd_ma, 'x', year);
    
    %%
    for i = 1:length(stressor)

        
        CQ = loadMatrix(wd.hd_strs, ['CQ_T_' stressor{i}], year, 'data');
        
        %%
        % Compute x_div
        x_div = computeXdiv(x);
        
        %%
        Q = CQ ./ x_div;  

        %%
        tic
        
        L_Q = Q' .* L;
        toc

            
        result = L_Q * Y_cty;

        %%
        rslt = reshape(result, [], 1);
        
        % Write to CSV
        savePath = fullfile(wd.hd_sa,'\4. Output\', [num2str(year) '_' stressor{i} '_T_BIFROST_Full_' num2str(gloria_vrs) '_country.csv']);
        writematrix(rslt, savePath);,

        clear result
        clear rslt
        
end

%% Helper Functions
function data = loadMatrix(path, prefix, year, varName)
    if nargin < 4
        varName = prefix;
    end
    data = load(fullfile(path, [prefix '_' num2str(year) '.mat']), varName).(varName);
end

function x_div = computeXdiv(x)
    x_div = x';
    x_div(x' == 0) = 1;
end

function reshaped = reshapeMatrix(matrix, matrixSize, segment)
    startIndices = 1:matrixSize:size(matrix, 1);
    endIndices = startIndices + segment;
    indices = arrayfun(@(s,e) s:e, startIndices, endIndices, 'UniformOutput', false);
    reshaped = matrix([indices{:}], :);
end