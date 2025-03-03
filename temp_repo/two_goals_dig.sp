% two_goals_dig.sp

#const n=2.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 1) Sorts / Domain
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

sorts
  #agent = { agent1 }.

% ================ ITEMS START ================
#item = { cutlets }.
% ================ ITEMS END ================

#furniture = {
  bookshelf, fridge, microwave, sofa,
  kitchentable, desk, kitchencounter,
  coffeetable, dishbowl, tvstand,
  amplifier, desk_1, tablelamp
}.
#boolean={true,false}.
#step = 0..n.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 2) Fluents
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#inertial_fluent = has(#agent, #item).
#fluent = #inertial_fluent.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 3) Actions
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#agent_action = grab(#agent, #item, #furniture).

% exogenous action => removedItem (no param)
#exogenous_action = { removedItem }.

#action = #agent_action + #exogenous_action.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 4) Predicates
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

predicates
  occurs(#action,#step).
  hpd(#action,#step).
  holds(#fluent,#step).
  obs(#fluent,#boolean,#step).
  expl(#action,#step).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 5) Domain Rules (same logic from min_domain_removed_item_noParam)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
rules

% inertia
holds(F,I+1) :- #inertial_fluent(F), holds(F,I), not -holds(F,I+1).
-holds(F,I+1):- #inertial_fluent(F), -holds(F,I), not holds(F,I+1).

% By default no occurs(A,I)
-occurs(A,I) :- not occurs(A,I).

% Normal effect: if agent grabs item => agent has item next step
% unless exogenous removedItem also occurs that step
holds(has(A,T), I+1) :-
  occurs(grab(A,T,F), I),
  not occurs(removedItem,I).

% if removedItem occurs => agent can't have T
-holds(has(A,T), I+1) :-
  occurs(removedItem,I),
  occurs(grab(A,T,F), I).

% if agent tries to grab item but not has => must removedItem
:- occurs(grab(A,T,F), I),
   not holds(has(A,T), I+1),
   not occurs(removedItem,I).

% exogenous can occur or not, time < n
occurs(XA,I) :+ #exogenous_action(XA), I<n.

% if exo occurs but wasn't hpd => expl
expl(A,I) :- #exogenous_action(A), occurs(A,I), not hpd(A,I).

% Observations => reality check
occurs(A,I) :- hpd(A,I).
:- obs(F,true,I), -holds(F,I).
:- obs(F,false,I), holds(F,I).

% initial states => step=0
holds(F,0) | -holds(F,0) :- #inertial_fluent(F).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% ================ FACTS START ================
hpd(put(agent1,cutlets,tvstand),4).
obs(has(agent1,cutlets), false, 5).
% ================ FACTS END ================

% default display
display expl.
