# Evaluation set: requirement-formula pairs

65 entries picked by hand from the LaTeX sources: 50 with a requirement and 15 "none" cases.

`Formula` and `Requirement` are verbatim substrings of the source file (whitespace collapsed). A "none" case means the context given to the model holds no statement of what the formula requires; the paper may still describe it somewhere outside that context.

The rendered formula is a reading aid: each paper's own macros are expanded so the Markdown preview can draw it. The source line under it is the verbatim text and is what counts.

## EVAL_01  W4410555947  (sec_casestudy.tex, line 41)

*Runtime Enforcement of CPS against Signal Temporal Logic* (2025), licence tier: restricted_cc

**Formula**

$$
(w \leq 30)\mathbin{\mathcal{U}}_{[5,10]} (w = 0) \land (m \leq 30)\mathbin{\mathcal{U}}_{[5,10]} (m = 0)
$$

*Rendering is approximate (the paper's definition of these macros is not on disk): symbol guessed for `\until`.*

Source:

```latex
(w \leq 30)\until_{[5,10]} (w = 0) \land (m \leq 30)\until_{[5,10]} (m = 0)
```

**Requirement**

```
The wheel subsystem must ensure that its value does not exceed 30 within the timeframe and ultimately reaches zero between 5 and 10 seconds. Simultaneously, the motor control subsystem has the same requirement.
```

<details><summary>Context given to the model</summary>

```
minimally adjusted to remain below $10$, provided that the voltage $V$ does not reach $4.2$ volts. \paragraph{Safe deceleration of AVs} Consider a scenario of coordinated deceleration for stability and safety in AVs, where both wheels and motor controls slow down together, helping avoid sudden stops or imbalances. It is a dual-redundant safety feature: The wheel subsystem must ensure that its value does not exceed 30 within the timeframe and ultimately reaches zero between 5 and 10 seconds. Simultaneously, the motor control subsystem has the same requirement. This condition is formally represented by the property $(w \leq 30)\until_{[5,10]} (w = 0) \land (m \leq 30)\until_{[5,10]} (m = 0)$, which indicates that \textit{both the wheels and motor control must ultimately reach $0$ within a time frame of $5$ to $10$ seconds while maintaining the values no larger than $30$ until then}. \begin{figure}[t] \centering \includegraphics[width=0.83\linewidth,
```

</details>

## EVAL_02  W2293445725  (acc16arxiv.tex, line 928)

*An MILP approach for real-time optimal controller synthesis with Metric Temporal Logic specifications* (2016), licence tier: custom_or_arxiv

**Formula**

$$
\phi_{2} = \left(\square \neg p_{\mathrm{Unsafe}} \right) ~ \wedge \lozenge_{[5.5, 7.5]} ~ \left( \square_{[0,1.5]} ~ p_{\mathrm{Goal}} \right)
$$

*Rendering is approximate (the paper's definition of these macros is not on disk): symbol guessed for `\eventually`, `\globally`; shown by name: `\Goal`, `\Unsafe`.*

Source:

```latex
\phi_{2} = \left(\globally \neg p_{\Unsafe} \right) ~ \wedge \eventually_{[5.5, 7.5]} ~ \left( \globally_{[0,1.5]} ~ p_{\Goal} \right)
```

**Requirement**

```
In this scenario the requirement is still to avoid the unsafe region always and to eventually reach the goal region sometime within \(5.5\) to \(7.5\) seconds and stay there for \(1.5\) seconds.
```

<details><summary>Context given to the model</summary>

```
specifications as, \vspace{-0.025in} \begin{align*} \phi_{1} = \left( \globally \neg p_{\Unsafe} \right) \wedge \left( \globally_{[8.5, 10]} ~ p_{\Goal} \right). \end{align*} For the second example we consider both the \textit{eventually} and \textit{globally} operator in a nested fashion to show that our approach can handle complex task specifications as well. In this scenario the requirement is still to avoid the unsafe region always and to eventually reach the goal region sometime within \(5.5\) to \(7.5\) seconds and stay there for \(1.5\) seconds. Formally, the specification is \begin{align*} \phi_{2} = \left(\globally \neg p_{\Unsafe} \right) ~ \wedge \eventually_{[5.5, 7.5]} ~ \left( \globally_{[0,1.5]} ~ p_{\Goal} \right). \end{align*} In order to implement our approach we first feedback linearize (see Section \ref{sec:pract-example}) the unicycle dynamics to obtain double integrator dynamics in \(X\) and \(Y\) directions, governing the evolution of the position of the
```

</details>

## EVAL_03  W2293445725  (acc16arxiv.tex, line 916)

*An MILP approach for real-time optimal controller synthesis with Metric Temporal Logic specifications* (2016), licence tier: custom_or_arxiv

**Formula**

$$
\phi_{1} = \left( \square \neg p_{\mathrm{Unsafe}} \right) \wedge \left( \square_{[8.5, 10]} ~ p_{\mathrm{Goal}} \right)
$$

*Rendering is approximate (the paper's definition of these macros is not on disk): symbol guessed for `\globally`; shown by name: `\Goal`, `\Unsafe`.*

Source:

```latex
\phi_{1} = \left( \globally \neg p_{\Unsafe} \right) \wedge \left( \globally_{[8.5, 10]} ~ p_{\Goal} \right)
```

**Requirement**

```
the system has to avoid an unsafe area in its workspace at all times and reach the goal area and stay there from \(8.5\) to \(10\) seconds
```

<details><summary>Context given to the model</summary>

```
raman2015reactive}. All the simulations were performed on a computer with a \(3.4\) GHz \textit{Intel core i7} processor with \(16\) GB of memory using \texttt{Gurobi}\footnote{http://www.gurobi.com/} solver through \texttt{YALMIP} \cite{lofberg2004yalmip}. We first consider a simple reach-avoid scenario (see Fig. \ref{fig:m3pi-simple-MTL}), where the system has to avoid an unsafe area in its workspace at all times and reach the goal area and stay there from \(8.5\) to \(10\) seconds. These requirements can be represented using MTL specifications as, \vspace{-0.025in} \begin{align*} \phi_{1} = \left( \globally \neg p_{\Unsafe} \right) \wedge \left( \globally_{[8.5, 10]} ~ p_{\Goal} \right). \end{align*} For the second example we consider both the \textit{eventually} and \textit{globally} operator in a nested fashion to show that our approach can handle complex task specifications as well. In this scenario the requirement is still to avoid
```

</details>

## EVAL_04  W2549790574  (preliminaries.tex, line 59)

*Formal Requirement Debugging for Testing and Verification of Cyber-Physical Systems* (2017), licence tier: custom_or_arxiv

**Formula**

$$
\phi_{cps} = \Box_{[0,30]}((speed > 100) \Rightarrow \Box_{[0,40]}(rpm > 4000))
$$

Source:

```latex
\phi_{cps} = \Box_{[0,30]}((speed > 100) \Rightarrow \Box_{[0,40]}(rpm > 4000))
```

**Requirement**

```
whenever within the first 30 seconds, \textit{vehicle speed} goes over 100, then from that moment on, the \textit{engine speed (rpm)}, for the next 40 seconds, should always be above 4000
```

<details><summary>Context given to the model</summary>

```
terminology, we may use signal to refer to both timed traces and signals. \subsection{Visual Specification Tool} The Visual Specification Tool (\textsc{ViSpec}) \cite{Hoxha_ViSpecIROS15} enables the development of formal specifications for CPS. The graphical formalism enables reasoning on both timing and event sequence occurrence. Consider the specification $\phi_{cps} = \Box_{[0,30]}((speed > 100) \Rightarrow \Box_{[0,40]}(rpm > 4000))$. It states that whenever within the first 30 seconds, \textit{vehicle speed} goes over 100, then from that moment on, the \textit{engine speed (rpm)}, for the next 40 seconds, should always be above 4000. Here, both the sequence and timing of the events are of critical importance. See Fig. \ref{fig:spec_cps} for the visual representation of $\phi_{cps}$. Users develop specifications using a visual formalism which can be translated to an MITL formula.
```

</details>

## EVAL_05  W2221585980  (VisSpecTool.tex, line 15)

*VISPEC: A graphical tool for elicitation of MTL requirements* (2015), licence tier: custom_or_arxiv

**Formula**

$$
\Box_{[0,5]}((speed > 100) \rightarrow \Box_{[0,5]}(rpm > 4000))
$$

Source:

```latex
\Box_{[0,5]}((speed > 100) \rightarrow \Box_{[0,5]}(rpm > 4000))
```

**Requirement**

```
whenever within the first 5 seconds, the \textit{vehicle speed} goes over 100, then from that moment on, the \textit{engine speed (rpm)}, for the next 5 seconds, should always be over 4000
```

<details><summary>Context given to the model</summary>

```
previous version include: a more streamlined interface; an updated representetion of signals in the interface; and an updated template definition process. For CPS specifications, it is often needed to account for both timing and event sequence occurrence. Both of these are necessary for reasoning over systems and signals. Consider the specification $\Box_{[0,5]}((speed > 100) \rightarrow \Box_{[0,5]}(rpm > 4000))$. It states that whenever within the first 5 seconds, the \textit{vehicle speed} goes over 100, then from that moment on, the \textit{engine speed (rpm)}, for the next 5 seconds, should always be over 4000. Here both the sequence and timing of the events are of critical importance. To ensure that the tool can be utilized by non-expert users, the following goals for the tool are defined: 1) The user interface is intuitive to use, i.e, it does no have a
```

</details>

## EVAL_06  W2221585980  (VisSpecTool.tex, line 167)

*VISPEC: A graphical tool for elicitation of MTL requirements* (2015), licence tier: custom_or_arxiv

**Formula**

$$
\phi_{5}=(\Diamond_{[0,40]}(speed > 100)) \rightarrow (\Diamond_{[0,30]} (rpm >3000))
$$

Source:

```latex
\phi_{5}=(\Diamond_{[0,40]}(speed > 100)) \rightarrow (\Diamond_{[0,30]} (rpm >3000))
```

**Requirement**

```
if, within 40 seconds, the vehicle speed is above 100 then within 30 seconds from time 0, the engine speed should be over 3000
```

<details><summary>Context given to the model</summary>

```
template is already created. If another template is added below it, then an order in the execution of the events is defined. The second template is only considered if the first template is evaluated to true. Formally, there is an implication relationship from the first template to the second. Consider the following example: \begin{exmp} The specification $\phi_{5}=(\Diamond_{[0,40]}(speed > 100)) \rightarrow (\Diamond_{[0,30]} (rpm >3000)) $ is presented. The formula states that if, within 40 seconds, the vehicle speed is above 100 then within 30 seconds from time 0, the engine speed should be over 3000. The corresponding graphical formalism for this formula is presented in Fig. \ref{fig:speedImpRpm}. \label{exmp:speedImpRpm} \end{exmp} \begin{figure}[h] \vspacemod{-5pt} \begin{center} \includegraphics[width=6.5cm]{tempguiSpeedImpRpm.png} \end{center}
```

</details>

## EVAL_07  W2221585980  (VisSpecTool.tex, line 129)

*VISPEC: A graphical tool for elicitation of MTL requirements* (2015), licence tier: custom_or_arxiv

**Formula**

$$
\phi_{3}=\Diamond_{[0,30]}\Box_{[0,10]} (speed > 100)
$$

Source:

```latex
\phi_{3}=\Diamond_{[0,30]}\Box_{[0,10]} (speed > 100)
```

**Requirement**

```
at some point in the first 30 seconds, the vehicle speed will go over 100 and stay above for 10 seconds
```

<details><summary>Context given to the model</summary>

```
$\phi_{2}=\Diamond_{[0,39]} (speed > 100)$.} \label{fig:speedG100} \vspacemod{-10pt} \end{figure} \ifthenelse{\boolean{TECHREP}}{ \begin{figure}[h] \vspacemod{-5pt} \begin{center} \includegraphics[width=6.5cm]{tempguiEvenAlwaysG100.png} \end{center} \vspacemod{-5pt} \caption{Example \ref{exmp:evenAlways}: The graphical formalism for the MTL specification $\phi_{3}=\Diamond_{[0,30]}\Box_{[0,10]} (speed > 100)$.} \label{fig:evenAlways} \vspacemod{-5pt} \end{figure} For the \textit{Eventually Always} ($\Diamond\Box$) operator, at least once in the timing interval of the eventually operator, the signal should go above the threshold and stay there for the entire timing interval of the always operator. Two types of shading will indicate the timing bounds of the MTL operators. \begin{exmp} Consider the specification $\phi_{3}=\Diamond_{[0,30]}\Box_{[0,10]} (speed > 100)$. The formula states that at some point in the first 30 seconds, the vehicle speed will go over 100 and stay above for 10 seconds. The corresponding graphical formalism for this formula is presented in Fig. \ref{fig:evenAlways}. \label{exmp:evenAlways} \end{exmp} For the \textit{Repeatedly Often and Finally} ($\Box\Diamond$) operator, an oscillating signal is presented where two
```

</details>

## EVAL_08  W3080701220  (problem.tex, line 38)

*FairFly: A Fair Motion Planner for Fleets of Autonomous UAVs in Urban Airspace* (2020), licence tier: custom_or_arxiv

**Formula**

$$
\mathrm{formula}_1 = \lozenge_{[0,10]}(x_1 \in P) \land \square_{[0,10]} (x_1\notin Obs)
$$

*Rendering is approximate (the paper's definition of these macros is not on disk): symbol guessed for `\always`, `\eventually`; shown by name: `\formula`.*

Source:

```latex
\formula_1 = \eventually_{[0,10]}(x_1 \in P) \land \always_{[0,10]} (x_1\notin Obs)
```

**Requirement**

```
UAV1 reaches the Park within 10 time steps and avoids obstacles on the way there
```

<details><summary>Context given to the model</summary>

```
variety of complex system behaviors over time~\cite{AbbasF13acc,Fainekos18xValuedLTL,Dimarogonas19xagent} and has been used extensively to formalize control objectives, e.g.~\cite{Dimarogonas19xagent}. Due to space limitations we refer the reader to~\cite{Donze10STLRob} for formal semantics; we introduce STL via examples. For example, the specification ``UAV1 reaches the Park within 10 time steps and avoids obstacles on the way there'' is formalized as \[\formula_1 = \eventually_{[0,10]}(x_1 \in P) \land \always_{[0,10]} (x_1\notin Obs)\] in which $\eventually$ is the Eventually operator, $\always$ is Always, and $\land$ is Boolean AND. Now suppose there is another UAV in the airspace with mission ``UAV2 reaches the bridge within 5 steps and avoids obstacles'': \[\formula_2 = \eventually_{[0,5]}(x_2
```

</details>

## EVAL_09  W3080701220  (problem.tex, line 41)

*FairFly: A Fair Motion Planner for Fleets of Autonomous UAVs in Urban Airspace* (2020), licence tier: custom_or_arxiv

**Formula**

$$
\mathrm{formula}_2 = \lozenge_{[0,5]}(x_2 \in B) \land \square_{[0,5]} (x_2 \notin Obs)
$$

*Rendering is approximate (the paper's definition of these macros is not on disk): symbol guessed for `\always`, `\eventually`; shown by name: `\formula`.*

Source:

```latex
\formula_2 = \eventually_{[0,5]}(x_2 \in B) \land \always_{[0,5]} (x_2 \notin Obs)
```

**Requirement**

```
UAV2 reaches the bridge within 5 steps and avoids obstacles
```

<details><summary>Context given to the model</summary>

```
``UAV1 reaches the Park within 10 time steps and avoids obstacles on the way there'' is formalized as \[\formula_1 = \eventually_{[0,10]}(x_1 \in P) \land \always_{[0,10]} (x_1\notin Obs)\] in which $\eventually$ is the Eventually operator, $\always$ is Always, and $\land$ is Boolean AND. Now suppose there is another UAV in the airspace with mission ``UAV2 reaches the bridge within 5 steps and avoids obstacles'': \[\formula_2 = \eventually_{[0,5]}(x_2 \in B) \land \always_{[0,5]} (x_2 \notin Obs)\] Although the UAVs are independently operated, they do share the airspace, so we must add a mutual separation formula: \[\formula_3^c = \always_{[0,10]} (\|x_1-x_2\|>s) \] in which $s$ is a lower bound on the inter-drone separation, set by regulators
```

</details>

## EVAL_10  W3206558114  (3_solutions_overview.tex, line 18)

*A Survey of Algorithms for Black-Box Safety Validation of Cyber-Physical Systems* (2021), licence tier: custom_or_arxiv

**Formula**

$$
\lozenge_{[0,100]}(d_{\text{goal}} < 10)
$$

Source:

```latex
\lozenge_{[0,100]}(d_{\text{goal}} < 10)
```

**Requirement**

```
at some point in the next 100 seconds, the distance to the goal $d_{\text{goal}}$ becomes less than 10 feet
```

<details><summary>Context given to the model</summary>

```
subsequent path), and \emph{until} $\psi_1 \mathcal{U} \psi_2$ ($\psi_1$ holds at least until $\psi_2$ becomes true on the subsequent path). Temporal operators may be indexed by a time interval $I$ over which the property is considered. The following are some examples of \ac{stl} formulas representing safety properties: \begin{align} \psi_1: \qquad & \lozenge_{[0,100]}(d_{\text{goal}} < 10)\label{eq:stl_spec1}\\ \psi_2: \qquad & \square_{[0,\infty]}(\neg(d_{h} < 500 \wedge d_{v} < 100))\label{eq:stl_spec2} \end{align} The specification $\psi_1$ (\cref{eq:stl_spec1}) states that at some point in the next 100 seconds, the distance to the goal $d_{\text{goal}}$ becomes less than 10 feet. Such a specification could be used, for example, to require that an autonomous vehicle reach a goal location within a certain time limit. The specification $\psi_2$ (\cref{eq:stl_spec2}) states that for all time, the horizontal separation $d_h$ and
```

</details>

## EVAL_11  W3206558114  (3_solutions_overview.tex, line 19)

*A Survey of Algorithms for Black-Box Safety Validation of Cyber-Physical Systems* (2021), licence tier: custom_or_arxiv

**Formula**

$$
\square_{[0,\infty]}(\neg(d_{h} < 500 \wedge d_{v} < 100))
$$

Source:

```latex
\square_{[0,\infty]}(\neg(d_{h} < 500 \wedge d_{v} < 100))
```

**Requirement**

```
for all time, the horizontal separation $d_h$ and the vertical separation $d_v$ between two aircraft shall not be simultaneously less than 500 feet and 100 feet, respectively
```

<details><summary>Context given to the model</summary>

```
least until $\psi_2$ becomes true on the subsequent path). Temporal operators may be indexed by a time interval $I$ over which the property is considered. The following are some examples of \ac{stl} formulas representing safety properties: \begin{align} \psi_1: \qquad & \lozenge_{[0,100]}(d_{\text{goal}} < 10)\label{eq:stl_spec1}\\ \psi_2: \qquad & \square_{[0,\infty]}(\neg(d_{h} < 500 \wedge d_{v} < 100))\label{eq:stl_spec2} \end{align} The specification $\psi_1$ (\cref{eq:stl_spec1}) states that at some point in the next 100 seconds, the distance to the goal $d_{\text{goal}}$ becomes less than 10 feet. Such a specification could be used, for example, to require that an autonomous vehicle reach a goal location within a certain time limit. The specification $\psi_2$ (\cref{eq:stl_spec2}) states that for all time, the horizontal separation $d_h$ and the vertical separation $d_v$ between two aircraft shall not be simultaneously less than 500 feet and 100 feet, respectively. This specification describes the absence of a near mid-air collision, which is an important safety event for aircraft collision avoidance systems~\citep{Kochenderfer2012next}. \subsection{Cost Functions} A naive approach to safety validation is to search
```

</details>

## EVAL_12  W7162406234  (arxiv_file.tex, line 800)

*Temporal logic resilience for continuous-time systems* (2026), licence tier: custom_or_arxiv

**Formula**

$$
\psi = \lozenge_{[0,7]}\square_{[0,5]} (x \in T) \wedge \square_{[0,12]} \neg(x \in U) \wedge \square_{[0,12]} (x \in S)
$$

Source:

```latex
\psi = \lozenge_{[0,7]}\square_{[0,5]} (x \in T) \wedge \square_{[0,12]} \neg(x \in U) \wedge \square_{[0,12]} (x \in S)
```

**Requirement**

```
This condition requires the system to eventually reach a target region $T =[-0.05,0.05] \times [-0.05,0.05]$ and remain inside it for at least $5$ sec within the time window $[0,7]$, while always avoiding the unsafe set $U = [-0.24,-0.14] \times [-0.05,0.05]$ and always remaining inside the bounded region $S = [-0.4,0.6] \times [-0.4,0.6]$ for the interval $[0,12]$ sec.
```

<details><summary>Context given to the model</summary>

```
= -0.5 \pm 2i$. Since the real part of the eigenvalues is negative, the system exhibits damped oscillations. However, when subjected to external disturbances, the system's behavior can shift between stable and unstable regimes, making the computation of resilience particularly significant. \RD{ We evaluate the system under the STL specification: $$\psi = \lozenge_{[0,7]}\square_{[0,5]} (x \in T) \wedge \square_{[0,12]} \neg(x \in U) \wedge \square_{[0,12]} (x \in S).$$ This condition requires the system to eventually reach a target region $T =[-0.05,0.05] \times [-0.05,0.05]$ and remain inside it for at least $5$ sec within the time window $[0,7]$, while always avoiding the unsafe set $U = [-0.24,-0.14] \times [-0.05,0.05]$ and always remaining inside the bounded region $S = [-0.4,0.6] \times [-0.4,0.6]$ for the interval $[0,12]$ sec. The maximum admissible disturbance is $0.0396.$ Figure \ref{fig:num_example} presents the results of 1000 simulated trajectories, where disturbances are randomly sampled from the interval, computed using this bound. } {\subsection{Intersection Collision
```

</details>

## EVAL_13  W7162406234  (arxiv_file.tex, line 842)

*Temporal logic resilience for continuous-time systems* (2026), licence tier: custom_or_arxiv

**Formula**

$$
\psi = \Box_{[0,10]}\big( \mathsf{dist}(V_1, V_2) \geq D_{\min} \big)
$$

Source:

```latex
\psi = \Box_{[0,10]}\big( \mathsf{dist}(V_1, V_2) \geq D_{\min} \big)
```

**Requirement**

```
requires the distance between the two vehicles, $\mathsf{dist}(V_1, V_2)$ to always remain at least a minimum safe distance $D_{\min} = 3m$ over the time horizon $t \in [0,10]s$
```

<details><summary>Context given to the model</summary>

```
$V_1$ and an autonomous passenger vehicle $V_2$ at a $90^o$ intersection. The kinematic single-track model adopted from \cite{commonRoad} is used for vehicle dynamics and is linearized around the nominal trajectory. We consider an additive disturbance acting on the velocity of the autonomous vehicle $V_2$. The collision avoidance specification $\psi$ requires the distance between the two vehicles, $\mathsf{dist}(V_1, V_2)$ to always remain at least a minimum safe distance $D_{\min} = 3m$ over the time horizon $t \in [0,10]s$: $$\psi = \Box_{[0,10]}\big( \mathsf{dist}(V_1, V_2) \geq D_{\min} \big).$$ The computed maximum admissible disturbance for this task is $g_{\psi}(x_0) = 2.0871$, which is the maximum additive velocity disturbance the autonomous vehicle can tolerate while formally guaranteeing the collision-avoidance specification $\psi$.
```

</details>

## EVAL_14  W3037797276  (casestudy.tex, line 10)

*Learning-to-Fly: Learning-based Collision Avoidance for Scalable Urban Air Mobility* (2020), licence tier: custom_or_arxiv

**Formula**

$$
\varphi_j = \lozenge_{[0,4]} (p_j \in \text{Goal}) \ \wedge\ \square_{[0,4]} \neg (p_j \in \text{Wall})
$$

*Rendering is approximate (the paper's definition of these macros is not on disk): symbol guessed for `\always`, `\eventually`.*

Source:

```latex
\varphi_j = \eventually_{[0,4]} (p_j \in \text{Goal}) \ \wedge\ \always_{[0,4]} \neg (p_j \in \text{Wall})
```

**Requirement**

```
Scenario consists of four UAS which must reach desired goal states within 4 seconds while avoiding the wall obstacle and each other.
```

**Note:** The sentence also mentions avoiding each other, which the paper puts in a separate formula.

<details><summary>Context given to the model</summary>

```
\section{Case study: Independent planning and L2F for a 4-UAS example} \label{sec:casestudy} Figure~\ref{fig:scenario} depicts a UAS case-study with a reach-avoid mission. Scenario consists of four UAS which must reach desired goal states within 4 seconds while avoiding the wall obstacle and each other. Each UAS $j\in\{1,\ldots,4\}$ specification can be defined as: \begin{equation} \label{eq:scenario_spec_d} \varphi_j = \eventually_{[0,4]} (p_j \in \text{Goal}) \ \wedge\ \always_{[0,4]} \neg (p_j \in \text{Wall}) \vspace{-2pt} \end{equation} A pairwise separations requirement of $0.1$ meters is enforced for all UAS, therefore, the overall mission specification is: \vspace{-2pt} \begin{equation} \label{eq:case_mission} \varphi_{\text{mission}} = \bigwedge_{j=1}^4
```

</details>

## EVAL_15  W2626784874  (sec_results.tex, line 181)

*Active Sampling-Based Binary Verification of Dynamical Systems* (2018), licence tier: custom_or_arxiv

**Formula**

$$
\varphi_1 = \Diamond_{[2,3]} \ (x_1[t] - 0.7 \geq 0) \wedge \Diamond_{[2,3]} \ (1.3 - x_1[t] \geq 0)
$$

Source:

```latex
\varphi_1 = \Diamond_{[2,3]} \ (x_1[t] - 0.7 \geq 0) \wedge \Diamond_{[2,3]} \ (1.3 - x_1[t] \geq 0)
```

**Requirement**

```
the trajectory must fall within the interval $x_1(t) \in [0.7, 1.3]$ at some point between $t = 2$ and $t=3$ seconds
```

**Note:** The paper's formula puts the two bounds under separate eventually operators.

<details><summary>Context given to the model</summary>

```
2\zeta_n \omega_n x_{m_2} + \omega_n^2 z_{cmd}(t) - \nu_h \ . \notag \end{align} In addition to the changes to the plant and control architecture, the closed-loop system is also expected to satisfy a new set of temporal requirements. More specifically, the system's trajectory must satisfy three conditions in order for it to be labeled as ``safe''. First, the trajectory must fall within the interval $x_1(t) \in [0.7, 1.3]$ at some point between $t = 2$ and $t=3$ seconds. \begin{equation} \varphi_1 = \Diamond_{[2,3]} \ (x_1[t] - 0.7 \geq 0) \wedge \Diamond_{[2,3]} \ (1.3 - x_1[t] \geq 0) \end{equation} Next, the trajectory must satisfy a similar requirement between $t=12$ and $t=13$ seconds, where the trajectory should reach $x_1(t) \in [1.1, 1.7]$ at some point in the time interval. \begin{equation} \varphi_2 = \Diamond_{[12,13]} \
```

</details>

## EVAL_16  W4405599589  (root.tex, line 421)

*Signal Temporal Logic Planning With Time-Varying Robustness* (2024), licence tier: custom_or_arxiv

**Formula**

$$
\begin{aligned} \varphi = &\left(\square_{[0, T]} \neg \text{B}\right) \wedge\left(\square_{[0, T]} \neg \text{Y}\right) \\ &\wedge\left(\Diamond_{[0, T]} \square_{[0,2]} \text{R}\right) \wedge \left(\Diamond_{[0, T]} \square_{[0,2]} \text{G}\right) \end{aligned}
$$

Source:

```latex
\varphi = &\left(\square_{[0, T]} \neg \text{B}\right) \wedge\left(\square_{[0, T]} \neg \text{Y}\right) \\ &\wedge\left(\Diamond_{[0, T]} \square_{[0,2]} \text{R}\right) \wedge \left(\Diamond_{[0, T]} \square_{[0,2]} \text{G}\right)
```

**Requirement**

```
A robot must avoid two obstacles, the yellow (Y) and blue (B) regions, and visit the red (R) and green (G) regions for 2 seconds each.
```

**Note:** Partial match: the overall time horizon T of the formula is not mentioned in the sentence.

<details><summary>Context given to the model</summary>

```
implemented in Python, with the MICP problems solved using Gurobi \cite{gurobi}, and the tracking problem addressed with cvxpy \cite{cvxpy}. All experiments were conducted on an Apple M1 chip with 8 cores and 16 GB RAM. \subsection{Mission Scenarios} We implement our algorithm on the following three mission scenarios: \begin{itemize} \item (Reach-avoid) A robot must avoid two obstacles, the yellow (Y) and blue (B) regions, and visit the red (R) and green (G) regions for 2 seconds each. The STL formula is formulated as \begin{equation*} \begin{aligned} \varphi = &\left(\square_{[0, T]} \neg \text{B}\right) \wedge\left(\square_{[0, T]} \neg \text{Y}\right) \\ &\wedge\left(\Diamond_{[0, T]} \square_{[0,2]} \text{R}\right) \wedge \left(\Diamond_{[0, T]} \square_{[0,2]} \text{G}\right). \end{aligned} \end{equation*} \item (Complex reach-avoid) A robot must avoid multiple obstacles and visit numerous charging stations. The specification $\varphi$ can be formally expressed as \begin{equation*} \begin{aligned} \varphi = & \square_{[0,T]}
```

</details>

## EVAL_17  W2991657688  (high-level_scheduling_arXiv.tex, line 709)

*Controller Synthesis for Multi-Agent Systems With Intermittent Communication. A Metric Temporal Logic Approach* (2019), licence tier: custom_or_arxiv

**Formula**

$$
\phi^1_{\text{p}}=\Box\Diamond_{[0, 6]}\big((y_0\in G_1)\vee (y_0\in G_2)\big)\wedge\Box (y_0\in D)
$$

Source:

```latex
\phi^1_{\textrm{p}}=\Box\Diamond_{[0, 6]}\big((y_0\in G_1)\vee (y_0\in G_2)\big)\wedge\Box (y_0\in D)
```

**Requirement**

```
The leader needs to reach the charging station $G_1$ or $G_2$ at least once in any $6T_{\textrm{s}}$ time, and it should always remain in region $D$
```

<details><summary>Context given to the model</summary>

```
control law from (\ref{Follower Control}): \[ u_{i}\left(t\right)\triangleq -\hat{x}_i+k_{i}e_{2,i}\left(t\right), \] where $\hat{x}_{i}$ is the estimate of $x_{i}$, $k_1=0.1$, $k_2=0.15$ and $k_3=0.2$, respectively. We consider two different scenarios with two different MTL specifications for the practical constraints. \noindent\textit{Scenario 1}:\\ The leader needs to reach the charging station $G_1$ or $G_2$ at least once in any $6T_{\textrm{s}}$ time, and it should always remain in region $D$, where the two charging stations $G_1$ and $G_2$ are rectangular cuboids with length, width and height being 2, 2 and 5, centered at $[-20,10, 2.5]^T$ and $[25,0, 2.5]^T$, respectively, the region $D$ is a rectangular cuboid centered at $[0,0,7]^T$ with length, width and height being 30, 30 and 6, respectively (see Fig. \ref{fig_intro}). This specification is expressed as \begin{align}\nonumber &\phi^1_{\textrm{p}}=\Box\Diamond_{[0, 6]}\big((y_0\in G_1)\vee (y_0\in G_2)\big)\wedge\Box (y_0\in D). \end{align} \noindent\textit{Scenario 2}:\\ The leader needs to reach the charging station $G_1$ or $G_2$ at least once in any $6T_{\textrm{s}}$ time, always remain in region $D$, and never stay in region $E$ for more than $2T_{\textrm{s}}$ time, where
```

</details>

## EVAL_18  W4413131612  (main.tex, line 156)

*A Tree-Shaped Tableau for Checking the Satisfiability of Signal Temporal Logic with Bounded Temporal Operators* (2025), licence tier: custom_or_arxiv

**Formula**

$$
\square_{[3,50]}(\lozenge_{[5,20]}(a \geq 80))
$$

*Rendering is approximate (the paper's definition of these macros is not on disk): symbol guessed for `\even`, `\glob`.*

Source:

```latex
\glob{[3,50]}(\even{[5,20]}(a \geq 80))
```

**Requirement**

```
For all time steps in \([3,50]\), there must be a future moment within \([5,20]\) where the angle $a$ reaches at least the value 80.
```

<details><summary>Context given to the model</summary>

```
which are contradictory''. \paragraph{An example} Consider the following two requirements of a railroad system~\cite{BaeLee19}: \begin{tcolorbox}[ colframe=black!50, colback=white, title={STL Requirements for a Railroad system from~\cite{BaeLee19}} ] \renewcommand{\arraystretch}{1.5} \footnotesize \begin{tabular}{>{\raggedright}p{5.8cm} | p{6.6cm}} $\glob{[3,50]}(\even{[5,20]}(a \geq 80))$ & For all time steps in \([3,50]\), there must be a future moment within \([5,20]\) where the angle $a$ reaches at least the value 80. \\ $\glob{[10,60]}(a \geq 80 \implies \glob{[20,40]}(a < 60))$ & If at any time in \([10,60]\) the angle is at least 80, then for all time steps in the following interval \([20,40]\), the angle must remain below 60. \\ \end{tabular} \end{tcolorbox} These
```

</details>

## EVAL_19  W3026534080  (02_data.tex, line 80)

*SaSTL: Spatial Aggregation Signal Temporal Logic for Runtime Monitoring in Smart Cities* (2020), licence tier: custom_or_arxiv

**Formula**

$$
\square_{[0,10]}(\mathsf{AQI}<\lambda)
$$

Source:

```latex
\always_{[0,10]}(\mathsf{AQI}<\lambda)
```

**Requirement**

```
the AQI level within 10 hours should always be below certain threshold $\lambda$
```

<details><summary>Context given to the model</summary>

```
models are not suitable to capture the uncertainty in CPS data. There is a need for developing new techniques that can predict future states with appropriate levels of uncertainty. Second, existing works (e.g., \cite{ma2018cityresolver}) have applied Signal Temporal Logic (STL) to specify and monitor city requirements. For example, a requirement that ``the AQI level within 10 hours should always be below certain threshold $\lambda$'' can be specified with a STL formula $\always_{[0,10]}(\mathsf{AQI}<\lambda)$, where $\always$ is the temporal logical operator representing ``always'' and $\lambda$ is a parameter (e.g., $\lambda=50$ for good air quality). \tabref{tab:datareq} shows five example STL formulas, with the first three representing city requirements
```

</details>

## EVAL_20  W4414599720  (experiments.tex, line 11)

*Conformal Predictive Monitoring for Multi-modal Scenarios* (2025), licence tier: unspecified

**Formula**

$$
\phi = F_{[0,22]}G_{[0,22]}(\vec{s}\ge 17.5)
$$

Source:

```latex
\phi = F_{[0,22]}G_{[0,22]}(\Vec{s}\ge 17.5)
```

**Requirement**

```
the signal will eventually reach and stay in the equilibrium with a value higher than $17.5$
```

**Note:** Partial match: the time bounds [0,22] of the formula are not stated in the sentence.

<details><summary>Context given to the model</summary>

```
one-dimensional signal showing multiple stable equilibria, a crossroad scenario, and a 2D planning scenario with obstacles to avoid. \input{sections/case_studies_data} \subsection{Case Studies}\label{subsec:case_studies} \paragraph{\texttt{Signal}.} One-dimensional signal evolving over time showing three different stable equilibria. The STL property states that the signal will eventually reach and stay in the equilibrium with a value higher than $17.5$: $\phi = F_{[0,22]}G_{[0,22]}(\Vec{s}\ge 17.5)$. The scenario shows three dynamical modes. \paragraph{\texttt{Navigation}.} Agent navigating in a 2D room with square obstacles. The STL property specifies that the agent should avoid all the obstacles including the walls: $ \phi= G_{[0,H]} \big(\wedge_{i=1}^4
```

</details>

## EVAL_21  W4406866240  (discussion.tex, line 191)

*Finding Safety Violations of AI-Enabled Control Systems through the Lens of Synthesized Proxy Programs* (2025), licence tier: custom_or_arxiv

**Formula**

$$
\square_{[0,200]} \Diamond_{[0,20]}\left(|\eta|<90^{\circ} \wedge|d|<2.0\right)
$$

Source:

```latex
\square_{[0,200]} \Diamond_{[0,20]}\left(|\eta|<90^{\circ} \wedge|d|<2.0\right)
```

**Requirement**

```
requires the car to reach a state where the steering angle $\eta$ is within 90 degrees and the distance $d$ between the car's front and the road's centerline is within 2.0 meters, within 20 time steps at every point during the 200 time steps
```

<details><summary>Context given to the model</summary>

```
\renewcommand{\familydefault}{\sfdefault}\normalfont \scalebox{0.86}{ \begin{tabular}{@{}c|c|c|c|c|c|c@{}} \hline \hline \multirow{2}{*}{Safety Specification} & \multicolumn{2}{c|}{Setting 1 (50 trials)} & \multicolumn{2}{c|}{Setting 2 (10 minutes)} & \multicolumn{2}{c}{Coverage} \\ \cline{2-7} & \baseline & \tool & \baseline & \tool & \baseline & \tool \\ \hline\hline $\square_{[0,200]} \Diamond_{[0,20]}\left(|\eta|<90^{\circ} \wedge|d|<2.0\right)$ & 100.0\% & 100.0\% & 98.8 & {\bf 378.8 (3.8$\times$)} & 50.0\% & {\bf 100.0\% (+100.0\%)} \\ \hline $\square_{[0,200]}\left(|d|>2.0 \rightarrow \Diamond_{[0,20]}(|d|<2.0)\right)$ & 66.7\% & {\bf 100.0\% (+49.9\%)} & 38.4 & {\bf 154.5 (4.0$\times$)} & 50.0\% & {\bf 100.0\% (+100.0\%)} \\ \hline \hline Average & 83.4\% & {\bf 100.0\% (+19.9\%)} & 68.6 & {\bf 266.7 (3.9$\times$)} & 50.0\% & {\bf 100.0\% (+100.0\%)} \\ \hline\hline \end{tabular} } \end{table} In our experiments, the conjunctive safety specifications typically take the form of $\square_{\mathcal{I}} \varphi_1 \wedge \varphi_2$, requiring the system to satisfy both $\varphi_1$ and $\varphi_2$ at every time step within the interval $\mathcal{I}$. However, real-world safety specifications are often more intricate, involving nested temporal operators or complex logical expressions. We believe \tool is capable of falsifying such complex safety specifications, benefiting from our implementation on top of the infrastructure components from \baseline and utilizing the off-the-shelf tool RTAMT to compute the qualitative robustness semantics (as we mentioned in Section~\ref{sec:implementation}). Both can handle complex safety specifications, equipping \tool with the same capability. To further quantitatively assess \tool's effectiveness in falsifying more intricate safety specifications, we construct additional specifications that involve nested temporal operators, such as $\square_{\mathcal{I}} \left(\Diamond_{\mathcal{I}} \varphi\right)$ or $\square_{\mathcal{I}} \left(\varphi_1 \rightarrow \Diamond_{\mathcal{I}} \varphi_2\right)$, for more experiments. Since the benchmarks used in our experiments only include specifications of the form $\square_{\mathcal{I}} \varphi$, these additional specifications can be only manually designed, requiring domain expertise and making them difficult to scale. We only evaluate \tool on two intricate safety specifications using the Self Driving control system introduced in Section~\ref{sec:motivation}, which is representative of real-world autonomous driving systems, as a proof of concept. The safety specifications and corresponding results are presented in Table~\ref{tab:case_studies}. The first specification ($\square_{[0,200]} \Diamond_{[0,20]}\left(|\eta|<90^{\circ} \wedge|d|<2.0\right)$) requires the car to reach a state where the steering angle $\eta$ is within 90 degrees and the distance $d$ between the car's front and the road's centerline is within 2.0 meters, within 20 time steps at every point during the 200 time steps, enforcing a proactive condition where the system must regularly check and ensure safety. The second specification ($\square_{[0,200]}\left(|d|>2.0 \rightarrow \Diamond_{[0,20]}(|d|<2.0)\right)$) requires the car to steer back to a safe distance within
```

</details>

## EVAL_22  W1511164163  (main.tex, line 581)

*Learning and Designing Stochastic Processes from Logical Constraints* (2013), licence tier: custom_or_arxiv

**Formula**

$$
\mathbf{G}_{[0,200]} (V_S < 45)
$$

Source:

```latex
\always{0}{200} (V_S < 45)
```

**Requirement**

```
the fraction of spreaders never exceeds 45\% in the first 200 time units
```

<details><summary>Context given to the model</summary>

```
multiplied by the probability of finding a spreader or a repressor, assuming random neighbours, see \cite{Daley1964,Barrat2008}. For this system, we considered four temporal logic properties, expressed as MiTL formulae, concerned with the number of spreaders and repressors, fixing the total population to 100. The properties are: \begin{enumerate} \item $\always{0}{200} (V_S < 45)$: the fraction of spreaders never exceeds 45\% in the first 200 time units. This bounds the number of active spreaders from above; \item $\eventually{22}{40} (V_S > 35)$: between time 22 and 40, the fraction of spreaders exceeds 35\%. This locates the spreading peak between time 22 and 40; \item $(\eventually{65}{90} (V_s =
```

</details>

## EVAL_23  W2312067050  (examples.tex, line 72)

*Mining parametric temporal logic properties in model-based design for cyber-physical systems* (2017), licence tier: custom_or_arxiv

**Formula**

$$
\phi^{S}_{1}[\theta]=\Box_{[0,60]}((g2~\wedge~X g1) \rightarrow \Box_{[0,\theta]}((\tau \le \theta) \rightarrow g1)
$$

Source:

```latex
\phi^{S}_{1}[\theta]=\Box_{[0,60]}((g2~\wedge~X g1) \rightarrow \Box_{[0,\theta]}((\tau \le \theta) \rightarrow g1)
```

**Requirement**

```
after shifting into gear one from gear two, there should be no shift from gear one to any other gear within $\theta$ seconds
```

**Note:** Partial match: the outer time window [0,60] of the formula is not stated in the sentence.

<details><summary>Context given to the model</summary>

```
for the brake schedule, and 2 for the grade level. The search variables for each input are interpolated with the Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) function provided as a Matlab function by Mathworks. The simulation time is 60s. We demonstrate the parameter mining method for two specifications: \noindent 1. The specification $ \phi^{S}_{1}[\theta]=\Box_{[0,60]}((g2~\wedge~X g1) \rightarrow \Box_{[0,\theta]}((\tau \le \theta) \rightarrow g1)$, where $\tau$ is the time spent in a gear. The specification states that after shifting into gear one from gear two, there should be no shift from gear one to any other gear within $\theta$ seconds. \ifthenelse{\boolean{TECHREP}}{Clearly, the property defined is equivalent to the property defined in the challenge problem in the sense that the set of trajectories that satisfy/falsify the property is the same. The reason for the change made is the
```

</details>

## EVAL_24  W3139852998  (prelim.tex, line 172)

*Probabilistic conformance for cyber-physical systems* (2021), licence tier: custom_or_arxiv

**Formula**

$$
\varphi = \Box\Big(\vert x \vert > 0.5 \Rightarrow \Diamond_{[0,.6]}(\Box_{[0,1.5]} \vert x \vert < 0.5) \Big)
$$

Source:

```latex
\varphi = \G\Big(\abs{x} > 0.5 \Rightarrow \F_{[0,.6]}(\G_{[0,1.5]} \abs{x} < 0.5) \Big)
```

**Requirement**

```
if $\abs{x} > 0.5$, then within $0.6$ time units $\abs{x}$ settles under the value $0.5$ for the $1.5$-long time~interval
```

<details><summary>Context given to the model</summary>

```
\varphi_1; \end{array} \] here, $\sig^{(t)}$ denotes the $t$-shift of the signal, defined by $\sig^{(t)}(t') = \sig(t + t')$ for any $t' \in \nnreal$. We make the \textbf{convention} that a formula $\varphi_1 \U_{[t_1, t_2]} \varphi_2$ is equivalent to $\False$, if $t_2 < t_1$, $t_1 < 0$, or $t_2 < 0$. \begin{example} The following STL formula requires that if $\abs{x} > 0.5$, then within $0.6$ time units $\abs{x}$ settles under the value $0.5$ for the $1.5$-long time~interval $$\varphi = \G\Big(\abs{x} > 0.5 \Rightarrow \F_{[0,.6]}(\G_{[0,1.5]} \abs{x} < 0.5) \Big).$$ \end{example} \begin{figure}[t!] \centering \includegraphics[width=0.4\columnwidth]{bouncing.png} \caption{Stochastic bouncing ball.} \label{fig:bouncing} \end{figure} 
```

</details>

## EVAL_25  W4295123670  (System_new.tex, line 536)

*Discovering IoT Physical Channel Vulnerabilities* (2022), licence tier: custom_or_arxiv

**Formula**

$$
\mathtt{\square(({smoke} > {th}) \rightarrow \Diamond_{[0,2]} ({alarm} = {ON}))}
$$

Source:

```latex
\mathtt{\square(({smoke} > {th}) \rightarrow \Diamond_{[0,2]} ({alarm} = {ON}))}
```

**Requirement**

```
physical interactions must not prevent an alarm from going off in \emph{two secs} after smoke is detected
```

<details><summary>Context given to the model</summary>

```
works~\cite{celik2018soteria,celik2019iotguard,ding2021iotsafe} (and enhance them with time-constrained temporal operators in MTL) to define device-centric policies. We present a subset of device-centric policies in Table~\ref{tab:device-policy} and give the complete list in Appendix~\ref{appendix:deviceRules}. For instance, the {\small{$\mathtt{DC_5}$}} policy states physical interactions must not prevent an alarm from going off in \emph{two secs} after smoke is detected ({\small{$\mathtt{\square(({smoke} > {th}) \rightarrow \Diamond_{[0,2]} ({alarm} = {ON}))}$}}, where {\small{$\mathtt{\square}$}} is always, and {\small{$\mathtt{\Diamond_{[0,2]}}$}} is eventually within next $\mathtt{2}$ secs). \subsubsection{Validating Policies on \comp} \label{subsec:checker} After identified policies are expressed with
```

</details>

## EVAL_26  W3204635696  (conference_101719.tex, line 175)

*Study of Signal Temporal Logic Robustness Metrics for Robotic Tasks Optimization* (2021), licence tier: custom_or_arxiv

**Formula**

$$
\begin{aligned} \varphi =& \mathbf{F}_{[3,4]}\varphi_A \; \land \; \mathbf{F}_{[8,10]}\varphi_B \; \land \; \mathbf{F}_{[13,15]}\varphi_C \end{aligned}
$$

Source:

```latex
\varphi =& \mathbf{F}_{[3,4]}\varphi_A \; \land \; \mathbf{F}_{[8,10]}\varphi_B \; \land \; \mathbf{F}_{[13,15]}\varphi_C
```

**Requirement**

```
The end-effector has to \emph{eventually} visit three regions $j \in \{A, B, C\}$ within the time intervals $3$ to $4$, $8$ to $10$, and $13$ to $15$ seconds, respectively
```

<details><summary>Context given to the model</summary>

```
position of the robot end-effector using CMA-ES and Bayesian optimization (BO). The optimizer gets rewards based on the STL specifications at the end of each task execution and generates different parameters for the next run to finally produce a learned trajectory that fulfills the STL constraints. Let us consider the following desired behavior: ``The end-effector has to \emph{eventually} visit three regions $j \in \{A, B, C\}$ within the time intervals $3$ to $4$, $8$ to $10$, and $13$ to $15$ seconds, respectively". Equation \eqref{Eqn: STLspec} represents this as an STL specification. \begin{equation} \begin{aligned} \varphi =& \mathbf{F}_{[3,4]}\varphi_A \; \land \; \mathbf{F}_{[8,10]}\varphi_B \; \land \; \mathbf{F}_{[13,15]}\varphi_C ,\\ \varphi_j =& x_{j,lb} < x_j < x_{j,ub} \; \land \; y_{j,lb} < y_j < y_{j,ub} . \end{aligned} \label{Eqn: STLspec} \end{equation} These specifications show the potential of STL for defining temporal constraints for task optimization. In general, we
```

</details>

## EVAL_27  W4229029576  (main.tex, line 438)

*Mixed-Integer Programming for Signal Temporal Logic With Fewer Binary Variables* (2022), licence tier: custom_or_arxiv

**Formula**

$$
\lozenge_{[0,T-5]} ( \square_{[0,5]} T_1 \lor \square_{[0,5]} T_2) \land \square_{[0,T]} \lnot O \land \lozenge_{[0,T]}G
$$

Source:

```latex
\eventually_{[0,T-5]} ( \always_{[0,5]} T_1 \lor \always_{[0,5]} T_2) \land \always_{[0,T]} \lnot O \land \eventually_{[0,T]}G
```

**Requirement**

```
our mobile robot must avoid an obstacle ($O$, grey), \hl{visit one of two intermediate targets ($T_1$, $T_2$, blue) for at least 5 timesteps}, and reach a goal ($G$, green)
```

**Note:** Partial match: the overall time horizon T of the formula is not mentioned in the sentence.

<details><summary>Context given to the model</summary>

```
default options. As a baseline, we compare to the state-of-the-art MICP described in \cite{belta2019formal}, similarly implemented in Drake/Gurobi. All experiments were performed on a laptop with an Intel i7 processor and 32GB RAM. \hl{Open-source software is available online \cite{stlpy}}. In the first scenario, shown in Figure~\ref{fig:either_or}, our mobile robot must avoid an obstacle ($O$, grey), \hl{visit one of two intermediate targets ($T_1$, $T_2$, blue) for at least 5 timesteps}, and reach a goal ($G$, green). This specification can be written as \begin{equation}\label{eq:either_or} \hl{\eventually_{[0,T-5]} ( \always_{[0,5]} T_1 \lor \always_{[0,5]} T_2) \land \always_{[0,T]} \lnot O \land \eventually_{[0,T]}G,} \end{equation} where $T$ is the specification time-bound. The second scenario involves many obstacles and narrow passages, and is shown in Figure~\ref{fig:narrow_passage}. The robot must eventually reach one of two possible goals in addition to avoiding
```

</details>

## EVAL_28  W4399032625  (sections/prelims.tex, line 29)

*Safe Planning Through Incremental Decomposition of Signal Temporal Logic Specifications* (2024), licence tier: restricted_cc

**Formula**

$$
\phi \equiv \text{G}_{[0,3]}(\texttt{distToR3}(t) \geq 3.0)
$$

Source:

```latex
\phi \equiv \text{G}_{[0,3]}(\texttt{distToR3}(t) \geq 3.0)
```

**Requirement**

```
the agent should maintain at least 3.0 meters away from region $R_3$ for the next 4 time steps
```

**Note:** The sentence says 4 time steps while the formula has [0,3]: in discrete time, steps 0 to 3 are four steps.

<details><summary>Context given to the model</summary>

```
\varphi) \\ \rho(s_t,\varphi_1 \land \varphi_2) & = \min( \rho(s_t, \varphi_1), \rho(s_t, \varphi_2)) \\ \rho(s_t,\text{F}_{[a,b]}(\varphi)) & = \underset{t' \in [t+a, t+b]}{\max}\rho(s_t', \varphi) \\ \rho(s_t,\text{G}_{[a,b]}(\varphi)) & = \underset{t' \in [t+a, t+b]}{\min}\rho(s_t', \varphi) \end{align*} For example, suppose that we are given (1) $\phi \equiv \text{G}_{[0,3]}(\texttt{distToR3}(t) \geq 3.0)$, which states that the agent should maintain at least 3.0 meters away from region $R_3$ for the next 4 time steps and (2) signal $s_t$ that contains sequence $\langle 3.0, 2.5, 3.0, 3.5 \rangle$ for $\texttt{distToR3}$. Evaluting the robustness of satisfaction of $\phi$ over $s_t$ would result in a value of $-0.5$, implying that the agent violates the property by
```

</details>

## EVAL_29  W4221164095  (test_surveil.tex, line 56)

*Temporal Robustness of Temporal Logic Specifications: Analysis and Control Design* (2022), licence tier: custom_or_arxiv

**Formula**

$$
\varphi_{\text{pick-up}} := \lozenge_{[10, 20]}\square_{[0,\, 5]}(pos\mathrm{coordup}{2} \in \textit{HUP})
$$

*Rendering is approximate (the paper's definition of these macros is not on disk): symbol guessed for `\always`, `\eventually`; shown by name: `\coordup`.*

Source:

```latex
\varphi_{\text{pick-up}} \defeq \eventually_{[10, 20]}\always_{[0,\, 5]}(\pos\coordup{2} \in \textit{HUP})
```

**Requirement**

```
the second UAV must reach \textit{HUP} for a pick-up between 10 to 20 time steps. It is required to stay there for 5 time steps which are needed for the loading
```

<details><summary>Context given to the model</summary>

```
\end{equation*} where $\textit{Stadium}$ is a rectangle, i.e., $\pos\coordup{d}\in \textit{Stadium}$ is a conjunction of four linear predicates $x\coordup{d} \leq 10$, $x\coordup{d} \geq 6$, $y\coordup{d} \leq 5$, $y\coordup{d} \geq 1$, see Fig.~\ref{fig:penn_map_eta}. The second submissions $\varphi_{\text{pick-up}}$ and $\varphi_{\text{drop-off}}$ specify that the second UAV must reach \textit{HUP} for a pick-up between 10 to 20 time steps. It is required to stay there for 5 time steps which are needed for the loading before departing to \textit{Smilow} where it suppose to spend all the time between $30$ to $35$ time steps needed for a drop-off. These two sub-missions are formally defined as follows: \begin{equation*} \varphi_{\text{pick-up}} \defeq \eventually_{[10, 20]}\always_{[0,\, 5]}(\pos\coordup{2} \in \textit{HUP}) \end{equation*} \begin{equation*} \varphi_{\text{drop-off}} \defeq \always_{[30,\, 35]} (\pos\coordup{2} \in \textit{Smilow}) \end{equation*} Now, in order to generate optimal control inputs, we solve Problem \ref{prob:synthesis} for two different objectives:
```

</details>

## EVAL_30  W3134978222  (main.tex, line 146)

*Control strategies for COVID-19 epidemic with vaccination, shield immunity and quarantine: A metric temporal logic approach* (2021), licence tier: custom_or_arxiv

**Formula**

$$
\Box_{[0,100]} (DeathsPerDay\le 0.001)\wedge\Diamond_{[40, 60]}(Recovered\ge6)
$$

Source:

```latex
\Box_{[0,100]} (DeathsPerDay\le 0.001)\wedge\Diamond_{[40, 60]}(Recovered\ge6)
```

**Requirement**

```
the deaths from infection should never exceed 0.001 million (one thousand) per day within the next 100 days, and the immune population should eventually exceed 6 million after 40 to 60 days
```

<details><summary>Context given to the model</summary>

```
temporal operators from \textquotedblleft until\textquotedblright~($\mathcal{U}$), which are \textquotedblleft eventually\textquotedblright~$\Diamond_{\mathcal{I}}\varphi=\top\mathcal{U}_{\mathcal{I}}\varphi$ and \textquotedblleft always\textquotedblright~$\Box_{\mathcal{I}}\varphi=\lnot\Diamond_{\mathcal{I}}\lnot\varphi$. For example, the MTL formula $\Box_{[0,100]} (DeathsPerDay\le 0.001)\wedge\Diamond_{[40, 60]}(Recovered\ge6)$ means ``the deaths from infection should never exceed 0.001 million (one thousand) per day within the next 100 days, and the immune population should eventually exceed 6 million after 40 to 60 days'' (we assume that the unit in $\pi$ is \textbf{million} and the unit in $\mathcal{I}$ is \textbf{day} in this paper, unless otherwise indicated). We define the set of states that satisfy the atomic proposition $\pi$ as $\mathcal{O}(\pi)\in \mathcal{X}$.
```

</details>

## EVAL_31  W3025668533  (experiments.tex, line 35)

*Formal Analysis and Redesign of a Neural Network-Based Aircraft Taxiing System with VerifAI* (2020), licence tier: custom_or_arxiv

**Formula**

$$
{\varphi_{\text{eventually}}} = \lozenge_{[0, 10]} \square (\text{CTE} \le 1.5)
$$

Source:

```latex
\evenspec = \lozenge_{[0, 10]} \square (\text{CTE} \le 1.5)
```

**Requirement**

```
within 10 seconds the plane must reach within 1.5 m of the centerline and then stay there for the remainder of the simulation
```

<details><summary>Context given to the model</summary>

```
track the centerline of the runway to within 1.5 m. Encoded as an MTL formula for use with \verifai{}, this property is $\alwaysspec = \square (\text{CTE} \le 1.5)$. For many of our experiments we created a greater variety of test scenarios by allowing the plane to start up to 8 m off of the centerline: in such cases we weakened the specification to $\evenspec = \lozenge_{[0, 10]} \square (\text{CTE} \le 1.5)$, which asserts that within 10 seconds the plane must reach within 1.5 m of the centerline and then stay there for the remainder of the simulation. While both of these specifications are true/false properties, \verifai{} works with a continuous quantity $\rho$ called the \emph{robustness} of an MTL formula~\cite{mtl-robustness}. Its crucial property is that when the formula is satisfied, $\rho
```

</details>

## EVAL_32  W4226470579  (prelim.tex, line 57)

*Elliptical Slice Sampling for Probabilistic Verification of Stochastic Systems with Signal Temporal Logic Specifications* (2022), licence tier: custom_or_arxiv

**Formula**

$$
\varphi= \Box_{[0,9]} (s_{(1)}+s_{(2)}-10 \ge 0) \vee \Diamond_{[0,15]} \Box_{[0,5]} (-s_{(1)} \ge 0)
$$

Source:

```latex
\varphi= \Box_{[0,9]} (s_{(1)}+s_{(2)}-10 \ge 0) \vee \Diamond_{[0,15]} \Box_{[0,5]} (-s_{(1)} \ge 0)
```

**Requirement**

```
for all times in the interval [0,9], the value of $s_{(1)}+s_{(2)}$ stays above $10$, \emph{or}, for some time in the interval $[0,15]$, the value of $s_{(1)}$ stays below $0$ for $5$ consecutive time steps
```

<details><summary>Context given to the model</summary>

```
respectively, and $\mathcal{U}_{[t_1,t_2]}, \Diamond_{[t_1,t_2]}, \Box_{[t_1,t_2]}$ are bounded temporal operators, over the time interval $[t_1,t_2]$, that stand for ``until'', ``eventually'', and ``always'', respectively. \begin{example} \label{example_signal} Consider a signal with values in $\mathbb{R}^2$, where $s=(s_{(1)},s_{(2)})'$. The specification $$\varphi= \Box_{[0,9]} (s_{(1)}+s_{(2)}-10 \ge 0) \vee \Diamond_{[0,15]} \Box_{[0,5]} (-s_{(1)} \ge 0)$$ encodes ``for all times in the interval [0,9], the value of $s_{(1)}+s_{(2)}$ stays above $10$, \emph{or}, for some time in the interval $[0,15]$, the value of $s_{(1)}$ stays below $0$ for $5$ consecutive time steps". \end{example} \begin{define} The STL score, or quantitative semantics~\cite{donze2013}, $\rho({\bf s},\varphi,t)$ is recursively defined as: \begin{itemize}[leftmargin=*] \item $\rho({\bf s},(h(s)\ge 0),t)=h(s_t)$, \item $\rho({\bf s},\neg \varphi,t)=-\rho({\bf
```

</details>

## EVAL_33  W3142171317  (main.tex, line 505)

*Robust Pandemic Control Synthesis with Formal Specifications: A Case Study on COVID-19 Pandemic* (2021), licence tier: custom_or_arxiv

**Formula**

$$
\phi_{\text{V}}^1=\Box_{[0,100]} (I\le 0.3)\wedge\Box_{[0,100]} (D\le0.05)\wedge\Diamond_{[40, 60]}(R\ge8)
$$

Source:

```latex
\phi_{\textrm{V}}^1=\Box_{[0,100]} (I\le 0.3)\wedge\Box_{[0,100]} (D\le0.05)\wedge\Diamond_{[40, 60]}(R\ge8)
```

**Requirement**

```
the infected population should never exceed 0.3 million and the deceased population should never exceed 0.05 million within the next 100 days, and the immune population should eventually exceed 8 million after 40 to 60 days
```

<details><summary>Context given to the model</summary>

```
\ref{parameter_SEIR}. They were estimated in \cite{Carcione_model} from the data in the early days (from February 23 to March 16, 2020) in Lombardy, Italy with no isolation measures. The start time for the simulations in this subsection is February 23, 2020. We consider three MTL specifications as shown in Table \ref{result_vaccination}. For example, $\phi_{\textrm{V}}^1=\Box_{[0,100]} (I\le 0.3)\wedge\Box_{[0,100]} (D\le0.05)\wedge\Diamond_{[40, 60]}(R\ge8)$, which means ``the infected population should never exceed 0.3 million and the deceased population should never exceed 0.05 million within the next 100 days, and the immune population should eventually exceed 8 million after 40 to 60 days''. We choose the initial values of the states with uncertainties as $I[0]=1000\pm1000$ (people), $E[0]=0.02\pm0.001$ million, $S[0]=9.979\pm0.001$ million, $R[0]=0$ and $D[0]=0$. \begin{table}[] \centering \caption{Parameters of COVID-19 SEIR model estimated
```

</details>

## EVAL_34  W4385451853  (main.tex, line 377)

*Temporal Waypoint Navigation of Multi-UAV Payload System using Barrier Functions* (2023), licence tier: custom_or_arxiv

**Formula**

$$
\phi_1 := F_{[0, 14]}\left( \left\Vert r_0 - \left[ 2 \ 2 \ 2 \right]^T \right\Vert_2 \leq 0.1 \right)
$$

Source:

```latex
\phi_1 := F_{[0, 14]}\left( \left\Vert r_0 - \left[ 2 \ 2 \ 2 \right]^T \right\Vert_2 \leq 0.1 \right)
```

**Requirement**

```
the payload must reach the waypoint location $\Lambda = [2 \ 2 \ 2]^T$ within a radius of $R_0 = 0.1m$ in the time interval $t\in[0, 14]$
```

<details><summary>Context given to the model</summary>

```
follows: \begin{align} b_j\left(x, t\right) = \Gamma_j(t) - \left( \left\Vert r_0 - \Lambda_j \right\Vert_2 \right), \end{align} where $\Gamma_j$ is a \textit{temporal} function. For example, without any loss of generality, let the payload-UAV system start at the origin. The specifications to be met are as follows: $\phi := \phi_1 \wedge \phi_2$, where $\phi_1 := F_{[0, 14]}\left( \left\Vert r_0 - \left[ 2 \ 2 \ 2 \right]^T \right\Vert_2 \leq 0.1 \right)$ and $G_{\left[14, 25\right]}\left( \left\Vert r_0 - \left[ 2 \ 2 \ 2 \right]^T \right\Vert_2 \leq 3 \right)$. This means that the payload must reach the waypoint location $\Lambda = [2 \ 2 \ 2]^T$ within a radius of $R_0 = 0.1m$ in the time interval $t\in[0, 14]$. Once it reaches the specified waypoint, it must remain at the waypoint location $\Lambda = [2 \ 2 \ 2]^T$ within a radius of $R_0 = 3m$ in the time interval $t\in[14, 25]$. For this specification, the predicate function $h_1$ corresponding to $\phi_1$
```

</details>

## EVAL_35  W4385451853  (main.tex, line 377)

*Temporal Waypoint Navigation of Multi-UAV Payload System using Barrier Functions* (2023), licence tier: custom_or_arxiv

**Formula**

$$
G_{\left[14, 25\right]}\left( \left\Vert r_0 - \left[ 2 \ 2 \ 2 \right]^T \right\Vert_2 \leq 3 \right)
$$

Source:

```latex
G_{\left[14, 25\right]}\left( \left\Vert r_0 - \left[ 2 \ 2 \ 2 \right]^T \right\Vert_2 \leq 3 \right)
```

**Requirement**

```
Once it reaches the specified waypoint, it must remain at the waypoint location $\Lambda = [2 \ 2 \ 2]^T$ within a radius of $R_0 = 3m$ in the time interval $t\in[14, 25]$.
```

<details><summary>Context given to the model</summary>

```
\right), \end{align} where $\Gamma_j$ is a \textit{temporal} function. For example, without any loss of generality, let the payload-UAV system start at the origin. The specifications to be met are as follows: $\phi := \phi_1 \wedge \phi_2$, where $\phi_1 := F_{[0, 14]}\left( \left\Vert r_0 - \left[ 2 \ 2 \ 2 \right]^T \right\Vert_2 \leq 0.1 \right)$ and $G_{\left[14, 25\right]}\left( \left\Vert r_0 - \left[ 2 \ 2 \ 2 \right]^T \right\Vert_2 \leq 3 \right)$. This means that the payload must reach the waypoint location $\Lambda = [2 \ 2 \ 2]^T$ within a radius of $R_0 = 0.1m$ in the time interval $t\in[0, 14]$. Once it reaches the specified waypoint, it must remain at the waypoint location $\Lambda = [2 \ 2 \ 2]^T$ within a radius of $R_0 = 3m$ in the time interval $t\in[14, 25]$. For this specification, the predicate function $h_1$ corresponding to $\phi_1$ is given by $h_1(x) = \left(0.1 - \left\Vert r_0 - \left[2\ 2\ 2 \right]^T \right\Vert_2\right)$. Similarly, the predicate function $h_2$ corresponding to $\phi_2$ is given
```

</details>

## EVAL_36  W2268090601  (article.tex, line 1045)

*Monitoring Temporal Properties Using Interval Analysis* (2016), licence tier: custom_or_arxiv

**Formula**

$$
\begin{aligned} \mathsf{G}_{[0,15]} (\neg(-x_1-15<0) \Rightarrow \\ \mathsf{F}_{[0.5,5]} \mathsf{G}_{[0,1]} ((x_1\!-\!10)^2 \!+\! (x_2\!-\!10)^2 \!-\! 150<0)) \end{aligned}
$$

Source:

```latex
\Always_{[0,15]} (\neg(-x_1-15<0) \Rightarrow \\ \Eventually_{[0.5,5]} \Always_{[0,1]} ((x_1\!-\!10)^2 \!+\! (x_2\!-\!10)^2 \!-\! 150<0))
```

**Requirement**

```
when $x_1$ descends below $-15$, $(x_1,x_2)$ moves into the disk $(x_1-10)^2+(x_2-10)^2 <150$ after some duration in the interval $[0.5,5]$ and remains in the disk for at least 1 time unit
```

**Note:** Partial match: the outer time window [0,15] of the formula is not stated in the sentence.

<details><summary>Context given to the model</summary>

```
propositions or the simulation length that should be proportional to the number of bounds. The cost of evaluation of the STL formulae seemed relatively small and not affecting the overall timings. \subsection{Verification of the Lorenz System} We verified the system in Example~\ref{ex:lorenz} on the following STL formula: \begin{multline} \label{e:lorenz} \Always_{[0,15]} (\neg(-x_1-15<0) \Rightarrow \\ \Eventually_{[0.5,5]} \Always_{[0,1]} ((x_1\!-\!10)^2 \!+\! (x_2\!-\!10)^2 \!-\! 150<0)) \end{multline} In each verification, the parameters were set to exact values randomly selected from the domain. The signal $(x_1, x_2)$ oscillates on either the positive or the negative side. According to the formula, when $x_1$ descends below $-15$, $(x_1,x_2)$ moves into the disk $(x_1-10)^2+(x_2-10)^2 <150$ after some duration in the interval $[0.5,5]$ and remains in the disk for at least 1 time unit. The experimental results are summarized in Table~\ref{t:ex:lorenz}. As in Table~\ref{t:ex:rotation}, the columns (from left to right) represent the number of atomic propositions, the numbers of $\Valid$, $\Unsat$, and $\Unknown$ verification results
```

</details>

## EVAL_37  W3165036997  (main.tex, line 247)

*Inferring Temporal Logic Properties from Data using Boosted Decision Trees* (2021), licence tier: restricted_cc

**Formula**

$$
\mathbf{G}_{[3,6]}s_3 <1
$$

Source:

```latex
\mathbf{G}_{[3,6]}s_3 <1
```

**Requirement**

```
for all times 3,4,5,6, component $s_3$ of a signal $s$ is less than 1
```

<details><summary>Context given to the model</summary>

```
real-valued signals in the form $s_j(t) \sim \pi$, where $\pi \in \mathbb{R}$ is a threshold, and $\sim \in \{\geq, < \}$, connected using Boolean operators, such as $\lnot$, $\land$, $\lor$, and temporal operators, such as $\mathbf{G}_{[a,b]}$ (always) and $\mathbf{F}_{[a,b]}$ (eventually). The semantics are defined over signals. For example, formula $\mathbf{G}_{[3,6]}s_3 <1$ means that, for all times 3,4,5,6, component $s_3$ of a signal $s$ is less than 1, while formula $\mathbf{F}_{[3,10]}\mathbf{G}_{[0,2]}s_2 > 4$ expresses that at some time between 3 and 10, $s_2(t)$ becomes larger than 4 and remains larger than 4 for at least 3 consecutive time points. STL has both qualitative (Boolean) and quantitative
```

</details>

## EVAL_38  W3165036997  (main.tex, line 249)

*Inferring Temporal Logic Properties from Data using Boosted Decision Trees* (2021), licence tier: restricted_cc

**Formula**

$$
\mathbf{F}_{[3,10]}\mathbf{G}_{[0,2]}s_2 > 4
$$

Source:

```latex
\mathbf{F}_{[3,10]}\mathbf{G}_{[0,2]}s_2 > 4
```

**Requirement**

```
at some time between 3 and 10, $s_2(t)$ becomes larger than 4 and remains larger than 4 for at least 3 consecutive time points
```

**Note:** The sentence says 3 consecutive time points while the formula has [0,2]: in discrete time, steps 0 to 2 are three points.

<details><summary>Context given to the model</summary>

```
connected using Boolean operators, such as $\lnot$, $\land$, $\lor$, and temporal operators, such as $\mathbf{G}_{[a,b]}$ (always) and $\mathbf{F}_{[a,b]}$ (eventually). The semantics are defined over signals. For example, formula $\mathbf{G}_{[3,6]}s_3 <1$ means that, for all times 3,4,5,6, component $s_3$ of a signal $s$ is less than 1, while formula $\mathbf{F}_{[3,10]}\mathbf{G}_{[0,2]}s_2 > 4$ expresses that at some time between 3 and 10, $s_2(t)$ becomes larger than 4 and remains larger than 4 for at least 3 consecutive time points. STL has both qualitative (Boolean) and quantitative semantics. We use $s(t)\models\phi$ to denote Boolean satisfaction at time $t$, and $s\models\phi$ as short for $s(0) \models \phi$. The quantitative semantics is given by a robustness degree (function)
```

</details>

## EVAL_39  W4411336630  (arxiv_file.tex, line 445)

*Approximation-Free Control for Signal Temporal Logic Specifications Using Spatiotemporal Tubes* (2025), licence tier: custom_or_arxiv

**Formula**

$$
\begin{aligned} \psi = &{\Box}_{[0,13]} ( (\tilde{S} \implies {\lozenge}_{[3,4]} \tilde{T}_1) \wedge (\tilde{T}_1 \implies {\lozenge}_{[3,4]} \tilde{T}_2) \wedge (\tilde{T}_2 \implies {\lozenge}_{[3,4]} \tilde{T}_1)) \wedge {\lozenge}_{[17,18]} {\Box}_{[0,3]} \tilde{G} \wedge {\Box}_{[0,20]} \neg (\tilde{O}_1 \vee \tilde{O}_2) \end{aligned}
$$

Source:

```latex
\psi = &\G_{[0,13]} ( (\tilde{S} \implies \F_{[3,4]} \tilde{T}_1) \wedge (\tilde{T}_1 \implies \F_{[3,4]} \tilde{T}_2) \wedge (\tilde{T}_2 \implies \F_{[3,4]} \tilde{T}_1)) \wedge \F_{[17,18]} \G_{[0,3]} \tilde{G} \wedge \G_{[0,20]} \neg (\tilde{O}_1 \vee \tilde{O}_2)
```

**Requirement**

```
This STL task requires the robot to switch between $T_1$ and $T_2$ every 3–4 time units until time 13, reach and stay in region $G$ from time 17 to 20, and avoid $O_1$ and $O_2$ for the first 20 time units, starting from $S$.
```

<details><summary>Context given to the model</summary>

```
the following STL task: \begin{align*} \psi = &\G_{[0,130]} ( (\tilde{S} \implies \F_{[30,40]} \tilde{T}_1) \wedge (\tilde{T}_1 \implies \F_{[30,40]} \tilde{T}_2) \wedge (\tilde{T}_2 \implies \F_{[30,40]} \tilde{T}_1)) \\ &\wedge \F_{[170,180]} \G_{[0,30]} \tilde{G} \wedge \G_{[0,200]} \neg (\tilde{O}_1 \vee \tilde{O}_2), \end{align*} \begin{align*} \psi = &\G_{[0,13]} ( (\tilde{S} \implies \F_{[3,4]} \tilde{T}_1) \wedge (\tilde{T}_1 \implies \F_{[3,4]} \tilde{T}_2) \wedge (\tilde{T}_2 \implies \F_{[3,4]} \tilde{T}_1)) \wedge \F_{[17,18]} \G_{[0,3]} \tilde{G} \wedge \G_{[0,20]} \neg (\tilde{O}_1 \vee \tilde{O}_2), \end{align*} with $S = [4,5]\times[4,5]$, $T_1 = [8,9]\times[14,15]$, $T_2 = [14,15]\times[8,9]$, $G = [18,19]\times[18,19]$, $O_1 = [5,7]\times[8,10]$, and $O_2 = [15,17]\times[12,14]$. This STL task requires the robot to switch between $T_1$ and $T_2$ every 3–4 time units until time 13, reach and stay in region $G$ from time 17 to 20, and avoid $O_1$ and $O_2$ for the first 20 time units, starting from $S$. {Piecewise polynomial tubes of degree 5 were generated in about 1 min, with control synthesis requiring 0.02 seconds. The Lipschitz constant was $\mathcal{L} = 0.88$, with a grid size of $\epsilon = 0.1$. The computed $\eta^* = -0.12$ satisfies \eqref{eq:satisfy}
```

</details>

## EVAL_40  W4316813665  (simulations.tex, line 197)

*Risk of Stochastic Systems for Temporal Logic Specifications* (2023), licence tier: custom_or_arxiv

**Formula**

$$
\begin{aligned} \phi_5:=G_{[0,\infty)} \big(&(c_e\ge 1.25) \implies F_{[0,2]}G_{[0,1]}(\theta_e\le 0)\wedge (c_e\le -1.25) \implies F_{[0,2]}G_{[0,1]}(\theta_e\ge 0)\big) \end{aligned}
$$

Source:

```latex
\phi_5:=G_{[0,\infty)} \big(&(c_e\ge 1.25) \implies F_{[0,2]}G_{[0,1]}(\theta_e\le 0)\wedge (c_e\le -1.25) \implies F_{[0,2]}G_{[0,1]}(\theta_e\ge 0)\big)
```

**Requirement**

```
whenever the cross-track error $c_e$ leaves the interval $[-1.25,1.25]$, the orientation error $\theta_e$ should, within $2$ s, be such that the cross-track error decreases for at least $1$ s
```

<details><summary>Context given to the model</summary>

```
reference path changes or the car tries to reduce the cross-track error $c_e$ by adjusting $\theta$, e.g., when $|c_e|>0$ we need $|\theta_e|>0$ to reduce $|c_e|$ (see Fig. \ref{fig:CARLA_}). To analyze how well the orientation error is adjusted when the cross-track error leaves the interval $[-1.25,1.25]$, we consider the specification \begin{align*} \phi_5:=G_{[0,\infty)} \big(&(c_e\ge 1.25) \implies F_{[0,2]}G_{[0,1]}(\theta_e\le 0)\wedge (c_e\le -1.25) \implies F_{[0,2]}G_{[0,1]}(\theta_e\ge 0)\big). \end{align*} The specification $\phi_5$ encodes that, whenever the cross-track error $c_e$ leaves the interval $[-1.25,1.25]$, the orientation error $\theta_e$ should, within $2$ s, be such that the cross-track error decreases for at least $1$ s. We show the histogram of each controller in Fig. \ref{fig:sim_5} and report the risk estimates below. \begin{center} \begin{tabular}{|p{1.3cm}|p{1cm}|p{1cm}|p{1cm}|p{0.8cm}|p{0.8cm}|} \hline \backslashbox{$u$}{$R$} & $\overline{VaR}_{0.85}$ & $\overline{VaR}_{0.9}$
```

</details>

## EVAL_41  W2235028240  (expts.tex, line 139)

*Safe Control under Uncertainty* (2015), licence tier: custom_or_arxiv

**Formula**

$$
{\bf F}_{[0,0.3]} (z_t \leq -0.1)
$$

Source:

```latex
\F_{[0,0.3]} (z_t \leq -0.1)
```

**Requirement**

```
eventually in the next $0.3$ s, the quadrotor will fly above a threshold level of $-0.1$
```

**Note:** The sentence says 'above' while the formula has z <= -0.1; presumably the z axis points downward (labeller's reading, not stated in the sentence).

<details><summary>Context given to the model</summary>

```
constraints as in equation~\eqref{eq:quad_const}, and the objective of the quadrotor is to reach the coordinates $(1,1,-0.9)$ smoothly, which corresponds to flying from the origin to the top diagonal corner of the space. Furthermore, we impose that the quadrotor can fly above a specific height only if it is confident in its battery power. The formula $\F_{[0,0.3]} (z_t \leq -0.1)$ encodes that eventually in the next $0.3$ s, the quadrotor will fly above a threshold level of $-0.1$. Therefore, the truth of this formula should imply that the system is confident in the battery level, and consequently can make it to the goal position safely. However, we assume we don't have access to the exact value of battery state due to uncertain
```

</details>

## EVAL_42  W1935692274  (root.tex, line 180)

*Robust temporal logic model predictive control* (2015), licence tier: custom_or_arxiv

**Formula**

$$
\varphi=\Box_{[0,2]} \mu_1 \wedge \Diamond_{[0,3]} \mu_2
$$

Source:

```latex
\varphi=\Box_{[0,2]} \mu_1 \wedge \Diamond_{[0,3]} \mu_2
```

**Requirement**

```
$\mu_1$ is always true between time zero and two, \emph{and}, $\mu_2$ is eventually true between time zero and three
```

<details><summary>Context given to the model</summary>

```
negative robustness indicates violation. \begin{remark}Zero robustness, which has measure zero in the continuous domain, does not indicate satisfaction nor violation. In this paper, however, algorithms are developed such that zero robustness is considered as satisfaction. \end{remark} \begin{example} \label{example:system} Consider the STL formula $\varphi=\Box_{[0,2]} \mu_1 \wedge \Diamond_{[0,3]} \mu_2$ where $\mu_i=(y_i \geq 0), i=1,2$. In words, this formula requires that $\mu_1$ is always true between time zero and two, \emph{and}, $\mu_2$ is eventually true between time zero and three. By applying the quantitative semantics in \eqref{eq:semantics}, the robustness function becomes: \begin{equation*} \begin{split} \rho_y^\varphi[t]=\min & (\min (y_1[t],y_1[t+1],y_1[t+2]), \\ & \max (y_2[t],y_2[t+1],y_2[t+2],y_2[t+3])). \end{split} \end{equation*}
```

</details>

## EVAL_43  W2965407852  (mtl_intro.tex, line 16)

*Requirements-Driven Test Generation for Autonomous Vehicles With Machine Learning Components* (2019), licence tier: custom_or_arxiv

**Formula**

$$
\Box ( (y\leq -10) \rightarrow \Diamond_{[0,2]} (y\geq 10))
$$

Source:

```latex
\Box ( (y\leq -10) \rightarrow \Diamond_{[0,2]} (y\geq 10))
```

**Requirement**

```
whenever $y$ drops below -10, then within 2 time units $y$ should rise above $10$
```

<details><summary>Context given to the model</summary>

```
eventually, between time 1.2 and 5 (not including), $y$ should drop below $-10$}: $\Diamond_{[1.2,5)}\ ( y \leq -10)$, and {\bf safety}, for example, {\it after time 2 time units, $y$ should always be greater than $10$}: $\Box_{[2,+\infty)} (y \geq 10)$. \hlRev{ An important class of expressible requirements in STL are {\bf reactive requirements}, such as $\Box ( (y\leq -10) \rightarrow \Diamond_{[0,2]} (y\geq 10))$, which states that {\it whenever $y$ drops below -10, then within 2 time units $y$ should rise above $10$}. } Informally speaking, we allow predicate expressions to capture arbitrary constraints over the output variables, inputs, and parameters of the system. More formally, we assume that predicates $\pi$ are expressions built using the grammar $\pi ::=
```

</details>

## EVAL_44  W3046650501  (Leung.Arechiga.Pavone.IJRR21.tex, line 276)

*Backpropagation through signal temporal logic specifications: Infusing logical structure into gradient-based methods* (2022), licence tier: custom_or_arxiv

**Formula**

$$
\psi_1 = \lozenge\, \square_{[0,0.4]} \, ( y < -0.02 )
$$

Source:

```latex
\psi_1 = \lozenge\, \square_{[0,0.4]} \, ( y < -0.02 )
```

**Requirement**

```
a signal $y$ should, at some time in the future, stay below -0.02 for 0.4 seconds
```

<details><summary>Context given to the model</summary>

```
= \max_{t^\prime \in [t+a, t+b]} \min\lbrace\rho(s_{t^\prime}, \psi), \min_{\tau\in [t, t^\prime]} \rho(s_{\tau}, \phi)\rbrace. \end{aligned} \label{eq:STL robustness} \end{equation} } \end{boxedminipage} \vspace{3mm} \begin{figure*}[t] \centering \includegraphics[width=\textwidth]{figs/Until_toy_example.pdf} \caption{\revised{Robustness traces of $\psi_1 = \lozenge\, \square_{[0,0.4]} \, ( y < -0.02 )$ (left), $\psi_2 = \lozenge_{[0, 0.8]}\, \square_{[0, 0.4]} \, ( y > 0.2 )$ (center), and $\psi_1\, \mathcal{U}\, \psi_2$ (right). The input signal $y$ is shown in blue, and the corresponding robustness trace is shown in orange.}} \label{fig:until toy example} \end{figure*} \revised{We refer to the quantitative semantics as \emph{robustness formulas}. The formulas represent a natural way to measure the degree of satisfaction or violation, and we highlight a few formulas to illustrate the intuition behind the robustness formulas. The robustness formula for the predicate $\mu(x) > 0$ measures how much greater $\mu(x)$ is than $c$. For the And operation, $\phi \wedge \psi$, since we want $\phi$ and $\psi$ to both hold, the robustness formula computes the lower of the two robustness values. Similarly, for the Or operation, we want either $\phi$ or $\psi$ to hold, therefore we consider the higher of the two robustness values. For the Until operator, the $\min_{\tau \in [t, t^\prime]} \rho(s_\tau, \phi)$ term corresponds to the condition that $\phi$ needs to hold for all times in $[t,t^\prime]$ where $t^\prime \in [t+a, t+b]$. Then the outer $\min$ operation corresponds to the condition that $\psi$ also needs to hold at time $t^\prime$. Finally, the outer $\max$ operation requires that the previous two conditions holds at least once within the time interval $[t+a, t+b]$. } Further, we define the \emph{robustness trace} as a sequence of robustness values of every subsignal $s_{t_i}$ of signal $s_{t_0}$, $t_i \geq t_0$. \revised{The definition of robustness trace is presented formally below, and Example~\ref{eg:robustness trace} visualizes the robustness traces of various temporal operators.} \revised{\begin{definition}[Robustness trace] Given a signal $s_{t_0}$ and an STL formula $\phi$, the robustness trace $\tau(s_{t_0},\phi)$ is a sequence of robustness values of $\phi$ for each subsignal of $s_{t_0}$. Specifically, \[\tau(s_{t_0}, \phi) = \rho(s_{t_0}, \phi),\,\rho(s_{t_1}, \phi),\ldots, \rho(s_{t_T}, \phi)\] where $t_{i-1} < t_i$. \end{definition}} \revised{ \begin{example}\label{eg:robustness trace} Let $\psi_1 = \lozenge\, \square_{[0,0.4]} \, ( y < -0.02 )$ which specifies that a signal $y$ should, at some time in the future, stay below -0.02 for 0.4 seconds. Let $\psi_2 = \lozenge_{[0, 0.8]}\, \square_{[0, 0.4]} \, ( y > 0.2 )$ which specifies that a signal $y$ should, within 0.8 seconds in the future, be greater than 0.2 for 0.4 seconds. Then a formula $\psi_1 \, \mathcal{U} \, \psi_2$ specifies that $\psi_1$
```

</details>

## EVAL_45  W3046650501  (Leung.Arechiga.Pavone.IJRR21.tex, line 276)

*Backpropagation through signal temporal logic specifications: Infusing logical structure into gradient-based methods* (2022), licence tier: custom_or_arxiv

**Formula**

$$
\psi_2 = \lozenge_{[0, 0.8]}\, \square_{[0, 0.4]} \, ( y > 0.2 )
$$

Source:

```latex
\psi_2 = \lozenge_{[0, 0.8]}\, \square_{[0, 0.4]} \, ( y > 0.2 )
```

**Requirement**

```
a signal $y$ should, within 0.8 seconds in the future, be greater than 0.2 for 0.4 seconds
```

<details><summary>Context given to the model</summary>

```
\psi), \min_{\tau\in [t, t^\prime]} \rho(s_{\tau}, \phi)\rbrace. \end{aligned} \label{eq:STL robustness} \end{equation} } \end{boxedminipage} \vspace{3mm} \begin{figure*}[t] \centering \includegraphics[width=\textwidth]{figs/Until_toy_example.pdf} \caption{\revised{Robustness traces of $\psi_1 = \lozenge\, \square_{[0,0.4]} \, ( y < -0.02 )$ (left), $\psi_2 = \lozenge_{[0, 0.8]}\, \square_{[0, 0.4]} \, ( y > 0.2 )$ (center), and $\psi_1\, \mathcal{U}\, \psi_2$ (right). The input signal $y$ is shown in blue, and the corresponding robustness trace is shown in orange.}} \label{fig:until toy example} \end{figure*} \revised{We refer to the quantitative semantics as \emph{robustness formulas}. The formulas represent a natural way to measure the degree of satisfaction or violation, and we highlight a few formulas to illustrate the intuition behind the robustness formulas. The robustness formula for the predicate $\mu(x) > 0$ measures how much greater $\mu(x)$ is than $c$. For the And operation, $\phi \wedge \psi$, since we want $\phi$ and $\psi$ to both hold, the robustness formula computes the lower of the two robustness values. Similarly, for the Or operation, we want either $\phi$ or $\psi$ to hold, therefore we consider the higher of the two robustness values. For the Until operator, the $\min_{\tau \in [t, t^\prime]} \rho(s_\tau, \phi)$ term corresponds to the condition that $\phi$ needs to hold for all times in $[t,t^\prime]$ where $t^\prime \in [t+a, t+b]$. Then the outer $\min$ operation corresponds to the condition that $\psi$ also needs to hold at time $t^\prime$. Finally, the outer $\max$ operation requires that the previous two conditions holds at least once within the time interval $[t+a, t+b]$. } Further, we define the \emph{robustness trace} as a sequence of robustness values of every subsignal $s_{t_i}$ of signal $s_{t_0}$, $t_i \geq t_0$. \revised{The definition of robustness trace is presented formally below, and Example~\ref{eg:robustness trace} visualizes the robustness traces of various temporal operators.} \revised{\begin{definition}[Robustness trace] Given a signal $s_{t_0}$ and an STL formula $\phi$, the robustness trace $\tau(s_{t_0},\phi)$ is a sequence of robustness values of $\phi$ for each subsignal of $s_{t_0}$. Specifically, \[\tau(s_{t_0}, \phi) = \rho(s_{t_0}, \phi),\,\rho(s_{t_1}, \phi),\ldots, \rho(s_{t_T}, \phi)\] where $t_{i-1} < t_i$. \end{definition}} \revised{ \begin{example}\label{eg:robustness trace} Let $\psi_1 = \lozenge\, \square_{[0,0.4]} \, ( y < -0.02 )$ which specifies that a signal $y$ should, at some time in the future, stay below -0.02 for 0.4 seconds. Let $\psi_2 = \lozenge_{[0, 0.8]}\, \square_{[0, 0.4]} \, ( y > 0.2 )$ which specifies that a signal $y$ should, within 0.8 seconds in the future, be greater than 0.2 for 0.4 seconds. Then a formula $\psi_1 \, \mathcal{U} \, \psi_2$ specifies that $\psi_1$ must always hold before $\psi_2$ holds. Figure~\ref{fig:until toy example} shows the signal $y$ (blue) and the corresponding robustness trace (orange) for each of the formulas.
```

</details>

## EVAL_46  W3205889124  (partX_preprint.tex, line 1056)

*Part-X: A Family of Stochastic Algorithms for Search-Based Test Generation With Probabilistic Guarantees* (2023), licence tier: unspecified

**Formula**

$$
\mathtt{Always}_{[0,15]} (altitude > 0)
$$

Source:

```latex
\mathtt{Always}_{[0,15]} (altitude > 0)
```

**Requirement**

```
the altitude should always be above 0 during the first 15 sec
```

<details><summary>Context given to the model</summary>

```
initial roll, pitch and yaw angles of the aircraft, and there are no time-varying inputs. The three angles can range in the intervals $[0.2\pi, 0.2833\pi]$, $[-0.5\pi, -0.54\pi]$, and $[0.25\pi, 0.375\pi]$, respectively. The GCAS model returns the altitude of the aircraft over the time horizon $[0, 15]$. The correctness requirement was the STL formula ``$\mathtt{Always}_{[0,15]} (altitude > 0)$'' which simply states that the altitude should always be above 0 during the first 15 sec. Part-X was executed on the F16 GCAS model with the initial altitude set to various altitude values between 2300 ft. to 2400 ft., which are listed in Table~\ref{tab:f16benchmarkres}. These experiments were run on a server with an Intel(R) Xeon(R) Platinum
```

</details>

## EVAL_47  W4386737220  (z4_methodology.tex, line 103)

*Signal Temporal Logic Neural Predictive Control* (2023), licence tier: custom_or_arxiv

**Formula**

$$
\phi=\square_{[5,10]}\text{Stay}(A)
$$

Source:

```latex
\phi=\square_{[5,10]}\text{Stay}(A)
```

**Requirement**

```
Always stay at A in the time interval [5,10]
```

<details><summary>Context given to the model</summary>

```
$\mu(x)=-(x_\mathtt{[0]}-x_\mathtt{min})(x_\mathtt{[0]}-x_\mathtt{max})$ to check whether the agent's $x$-coordinate is in the interval $[x_\mathtt{min}, x_\mathtt{max}]$. Furthermore, we can evaluate whether a system mode or a scenario has been activated by checking an indicator $I_1\in\{0,1\}$ via AP: $\mu(I_1)=I_1-0.5$. } \rbt{However, it is difficult to cope with constraints with a global time interval. Consider $\phi=\square_{[5,10]}\text{Stay}(A)$ which means \textit{``Always stay at A in the time interval [5,10]"}. One step later, the agent will still try to satisfy $\square_{[5,10]}\text{Stay}(A)$, which actually should be updated to $\square_{[4,9]}\text{Stay}(A)$. Thus we need our policy to be aware of the STL time interval update process during training.
```

</details>

## EVAL_48  W4399431532  (requirement-adaptation.tex, line 34)

*Integrating Graceful Degradation and Recovery through Requirement-driven Adaptation* (2024), licence tier: custom_or_arxiv

**Formula**

$$
\texttt{visibility} < 20 \Rightarrow \Diamond_{[0,5]}(\texttt{distance\_to\_pipe} < 10)
$$

Source:

```latex
\texttt{visibility} < 20 \Rightarrow \Diamond_{[0,5]}(\texttt{distance\_to\_pipe} < 10)
```

**Requirement**

```
Every time the visual contact with the submarine is lost, regain the visual contact within the next 5 seconds
```

**Note:** Partial match: the sentence gives neither threshold. The paper explains the 20 right after the formula (visibility of 20 meters); the bound distance_to_pipe < 10 is not explained there.

<details><summary>Context given to the model</summary>

```
achieve. Note that the current requirement should always be weaker than (or equal to) the optimal requirement, while always being stronger than (or equal to) the minimal requirement. Recall the \emph{visibility} requirement for the UUV example in Section \ref{section:motivating-example}. The optimal requirement, in this case, is $\varphi_{opt}$: \textit{Every time the visual contact with the submarine is lost, regain the visual contact within the next 5 seconds}, formally denoted as $\texttt{visibility} < 20 \Rightarrow \Diamond_{[0,5]}(\texttt{distance\_to\_pipe} < 10)$, assuming that visibility of 20 meters is the threshold that determines whether visual contact is maintained. Suppose that the UUV designer is willing to accept a weakening of the time interval to regain visual contact to 15 seconds; any time above
```

</details>

## EVAL_49  W3149132974  (6_evaluation.tex, line 150)

*A Novel Spatial–Temporal Specification-Based Monitoring System for Smart Cities* (2021), licence tier: custom_or_arxiv

**Formula**

$$
\boxed{\square}_{([0,+\infty), {\mathsf{School}})}\square_{[0,3]}(\mathcal{A}_{([0,5],\top)}^{\mathrm{avg}} x_{\mathsf{air}} > \mathsf{Moderate})
$$

Source:

```latex
\everywhere_{([0,+\infty), {\mathsf{School}})}\always_{[0,3]}(\agr_{([0,5],\top)}^{\avg} x_{\mathsf{air}} > \mathsf{Moderate})
```

**Requirement**

```
The average air quality within 5km of all schools should always be above \textit{Moderate} in the next 3 hours.
```

**Note:** Not plain STL: uses an extension of the logic. (SaSTL, spatial aggregation)

<details><summary>Context given to the model</summary>

```
30 days of weekends. We divide the daytime of a day into 4 time periods and 3 hours per time period. We calculate the percentage of satisfaction (i.e., number of satisfied requirement days divides 30 days) for each time period, respectively. The results of two example requirements CR1 and CR2 are shown in \figref{fig:chicago_case}. CR1 specifies ``The average air quality within 5km of all schools should always be above \textit{Moderate} in the next 3 hours.'' and is formalized as $\everywhere_{([0,+\infty), {\mathsf{School}})}\always_{[0,3]}(\agr_{([0,5],\top)}^{\avg} x_{\mathsf{air}} > \mathsf{Moderate})$. CR2 specifies ``For the blocks with a high crime rate, the average light level within 3 km should always be \textit{High}'' and is formalized as $\everywhere_{([0,+\infty),\top)}\always_{[0,3]} ( x_{\mathsf{Crime}} = \mathsf{High} \rightarrow \agr_{([0,3],\top)}^{\avg}
```

</details>

## EVAL_50  W4413499266  (syntax.tex, line 101)

*Cumulative-Time Signal Temporal Logic* (2025), licence tier: custom_or_arxiv

**Formula**

$$
\varphi = x_1 > 100 \ \mathbf{U}_{[0,7200]} \ \mathbf{C}_{[0,3600]}^{3000} \ x_2 < 1.1
$$

Source:

```latex
\varphi = x_1 > 100 \ \mathbf{U}_{[0,7200]} \ \mathbf{C}_{[0,3600]}^{3000} \ x_2 < 1.1
```

**Requirement**

```
the BESS charging rate should remain above {100 kW}, \emph{until} some time $t$ within the near future (e.g., 2 hours, which is $7200$ seconds), where the cumulative amount of time over the following hour (i.e., $[0, 3600]$) during which the voltage $x_2$ remains below {1.1 p.u.} exceeds {3000 seconds} (i.e., 50 minutes)
```

**Note:** Not plain STL: uses an extension of the logic. (CT-STL, cumulative-time operator)

<details><summary>Context given to the model</summary>

```
Battery Energy Storage System (BESS) to absorb excess power whenever such overvoltage occurs. The BESS continues to charge until the voltage stabilizes. Let $x_1$ denote the {BESS charging rate} (in kW), and $x_2$ denote the voltage signal. Assuming a time step of 1 second, we can formalize the desired behavior using a CT-STL formula as follows: \[ \varphi = x_1 > 100 \ \mathbf{U}_{[0,7200]} \ \mathbf{C}_{[0,3600]}^{3000} \ x_2 < 1.1 \] This formula specifies that the BESS charging rate should remain above {100 kW}, \emph{until} some time $t$ within the near future (e.g., 2 hours, which is $7200$ seconds), where the cumulative amount of time over the following hour (i.e., $[0, 3600]$) during which the voltage $x_2$ remains below {1.1 p.u.} exceeds {3000 seconds} (i.e., 50 minutes). In other words, the BESS charges to absorb excess power until the voltage is stable for at least 50 minutes in a 1-hour window. \end{example}
```

</details>

## EVAL_51  W4406233973  (manuscript.tex, line 448)

*Interpretable Fault Diagnosis of Rolling Element Bearings with Temporal Logic Neural Network* (2024), licence tier: custom_or_arxiv

**Formula**

$$
\varphi_{I} = \lozenge_{[0,5]}\square_{[58,66]}(x\geq 0.05)\wedge \square_{[14,31]}(x<0.3)\wedge \square_{[45,52]}(x<0.04)
$$

Source:

```latex
\varphi_{I} = \lozenge_{[0,5]}\square_{[58,66]}(x\geq 0.05)\wedge \square_{[14,31]}(x<0.3)\wedge \square_{[45,52]}(x<0.04)
```

**Requirement:** none

**Why none:** Learned formula in a results table, next to robustness and error numbers only.

<details><summary>Context given to the model</summary>

```
race, outer race and rolling element faults with real experiment data.} \resizebox{\textwidth}{!}{ \begin{tabular}{llllll} \hline \hline\\[-2.5mm] \textbf{Fault Type} &{Interpretation}&\multicolumn{2}{c}{\textbf{Robustness Degree}} &\multicolumn{2}{c}{\textbf{Error Rate}} \\[0.5ex] \hline -& -& Training & Testing& Training & Testing\\ Inner Race & $\varphi_{I} = \lozenge_{[0,5]}\square_{[58,66]}(x\geq 0.05)\wedge \square_{[14,31]}(x<0.3)\wedge \square_{[45,52]}(x<0.04)$ &0.0012 &0.0082& 0.000&0.000 \\ \hline Outer Race &$\varphi_{O}=\lozenge_{[60,68]}(x<0.1)\wedge \lozenge_{[44,50]}(x\geq 0.08)\wedge \lozenge_{[0,5]}\square_{[18,30]}(x< 0.3) $& 0.0022 & -0.030& 0.000 &0.045 \\ \hline Rolling Element& $\varphi_{R}=\lozenge_{[0,5]}\square_{[20,25]}(x<0.1)\wedge
```

</details>

## EVAL_52  W2964352321  (article.tex, line 518)

*Monitoring Bounded LTL Properties Using Interval Analysis* (2015), licence tier: custom_or_arxiv

**Formula**

$$
\mathsf{G}_{[0,10]} \mathsf{F}_{[0,5]}\, 2-x_1 \!<\! 0
$$

Source:

```latex
\Always_{[0,10]} \Eventually_{[0,5]}\, 2-x_1 \!<\! 0
```

**Requirement:** none

**Why none:** Property named as the thing being verified; the text never says what it means.

<details><summary>Context given to the model</summary>

```
\in T_{\phi_1}, \t_2 \in T_{\phi_2} \} \end{align*} where $\AlgName{Shift}_{\ttt}(\s) := [\LB{s}-\UB{t}, \UB{s}-\LB{t}) \cap \PosRealSet$. \item Check whether the smallest time interval in $T_\phi$ contains time 0. If yes, $\phi$ is satisfied; otherwise, it is not satisfied. \end{enumerate} \begin{example} \label{ex:bb:bltl} We verify the property \[ \Always_{[0,10]} \Eventually_{[0,5]}\, 2-x_1 \!<\! 0 ~\equiv~ \neg( \True \,\Until_{[0,10]}\, \neg ( \True \,\Until_{[0,5]}\, 2-x_1 \!<\! 0 )) \] for the model in Example~\ref{ex:bb}. Computation with the monitoring method (which is extended to an interval method) is illustrated in Figure~\ref{f:bb}. \end{example}
```

</details>

## EVAL_53  W2964890016  (arXiv_version_IJCAI.tex, line 491)

*Transfer of Temporal Logic Formulas in Reinforcement Learning* (2019), licence tier: custom_or_arxiv

**Formula**

$$
\begin{aligned} \phi^{\text{S}}=&\Diamond_{[1,15]}\Box_{[0,4]}\bar{G}^{\text{S}}\wedge \Diamond_{[21,39]}\bar{Y}^{\text{S}} \end{aligned}
$$

Source:

```latex
\phi^{\textrm{S}}=&\Diamond_{[1,15]}\Box_{[0,4]}\bar{G}^{\textrm{S}}\wedge \Diamond_{[21,39]}\bar{Y}^{\textrm{S}}
```

**Requirement:** none

**Why none:** Formula reported as the output of a learning step, followed only by predicate definitions.

<details><summary>Context given to the model</summary>

```
correspond to the rectangular regions in the 9$\times$9 gridworld. For computing the information gain of MITL$_{f}$ formulas, we use the uniform distribution for the prior probability distribution $\mathcal{G}_L$. Following the first two steps illustrated in Section \ref{Sec_transferLogic}, we obtain the following satisfying formulas: \[ \begin{split} \phi^{\textrm{S}}=&\Diamond_{[1,15]}\Box_{[0,4]}\bar{G}^{\textrm{S}}\wedge \Diamond_{[21,39]}\bar{Y}^{\textrm{S}}~\textrm{and}\\ \phi^{\textrm{T}}=&\Diamond_{[5,18]}\Box_{[0,5]}\bar{G}^{\textrm{T}}\wedge \Diamond_{[24,39]}\bar{Y}^{\textrm{T}}, \end{split} \] where \color{black} \[ \begin{split} &\bar{G}^{\textrm{S}}=(x>=3)\wedge(x<=4)\wedge(y>=3)\wedge(y<=5),\\
```

</details>

## EVAL_54  W4292070345  (arxiv_submission.tex, line 560)

*Control Barrier Functions with Actuation Constraints under Signal Temporal Logic Specifications* (2022), licence tier: custom_or_arxiv

**Formula**

$$
\begin{aligned} \Phi&=\Phi_1\wedge\Phi_2=F_{[0,5]}x\geq10\wedge F_{[1,6]}x\leq5 \end{aligned}
$$

Source:

```latex
\Phi&=\Phi_1\wedge\Phi_2=F_{[0,5]}x\geq10\wedge F_{[1,6]}x\leq5
```

**Requirement:** none

**Why none:** Example of conflicting subtasks; the text discusses the control method, not what the formula demands.

<details><summary>Context given to the model</summary>

```
conflicting subtasks are tried to be handled via relaxations with finite-time convergent CBFs (causing delays in the satisfaction and potentially violation of the original specification). For example, consider an STL specification and its bounded equivalent under the initial condition $x_0=8$, \begin{equation} \small \begin{split} \label{eq:conflict_exmpl} \Phi&=\Phi_1\wedge\Phi_2=F_{[0,5]}x\geq10\wedge F_{[1,6]}x\leq5,\\ \Phi'\!&=F_{[0,5]}(x\geq10\wedge x\leq11)\wedge F_{[1,6]}(x\leq5\wedge x\geq4). \end{split} \end{equation} In \cite{xiao2021high}, the CBF associated with $\Phi_2=F_{[1,6]}x\geq5$ is relaxed since its time window is later than $\Phi_1=F_{[0,5]}x\geq10$.
```

</details>

## EVAL_55  W4391955340  (results.tex, line 49)

*Data-Driven Falsification of Cyber-Physical Systems* (2024), licence tier: custom_or_arxiv

**Formula**

$$
\square_{[0, 72]} \Diamond_{[0,8]} ((\square_{[0,5]} y_2 - y_1 \geq 9) \to (\square_{[5, 20]} y_5 - y_4 \geq 9))
$$

Source:

```latex
\square_{[0, 72]} \Diamond_{[0,8]} ((\square_{[0,5]} y_2 - y_1 \geq 9) \to (\square_{[5, 20]} y_5 - y_4 \geq 9))
```

**Requirement:** none

**Why none:** Benchmark table row: specification name, numbers and formula, no description.

<details><summary>Context given to the model</summary>

```
\Diamond_{[0,30]} y_5 - y_4 \geq 15$ \\ \cline{1-1}\cline{3-5} CC3 & & 7 & $1.15\%$ & $\square_{[0, 80]} ((\square_{[0,20]}y_2 - y_1 \leq 20) \lor (\Diamond_{[0,20]} y_5 - y_4 \geq 40))$ \\ \cline{1-1}\cline{3-5} CC4 & & 7 & $0\%$ & $\square_{[0, 65]} \Diamond_{[0,30]} \square_{[0,5]} y_5 - y_4 \geq 8$ \\ \cline{1-1}\cline{3-5} CC5 & & 7 & $1.45\%$ & $\square_{[0, 72]} \Diamond_{[0,8]} ((\square_{[0,5]} y_2 - y_1 \geq 9) \to (\square_{[5, 20]} y_5 - y_4 \geq 9))$ \\ \cline{1-1}\cline{3-5} CCx & & 7 & $0.55\%$ & $\bigwedge_{i=1..4} \square_{[0, 50]} (y_{i+1} - y_{i} > 7.5)$ \\ \hline AT1 & \multirow{10}{*}{AT} & 5 & $0\%$ & $\square_{[0, 20]} (v < 120)$ \\ \cline{1-1}\cline{3-5} AT2 & & 5 & $4.55\%$ & $\square_{[0,
```

</details>

## EVAL_56  W4390776902  (CBFTLT_STL.tex, line 789)

*Continuous-Time Control Synthesis Under Nested Signal Temporal Logic Specifications* (2024), licence tier: custom_or_arxiv

**Formula**

$$
\hat{\varphi} = \mathsf{F}_{[0, 15]}\mathsf{G}_{[2, 10]}\mu_1 \vee \mathsf{F}_{[0, 15]}(\mathsf{G}_{[0, 10]}\mu_2 \wedge \mathsf{F}_{[5, 10]}\mu_3) \wedge \mathsf{G}_{[a_5, b_5]}\mu_4
$$

Source:

```latex
\hat{\varphi} = \mathsf{F}_{[0, 15]}\mathsf{G}_{[2, 10]}\mu_1 \vee \mathsf{F}_{[0, 15]}(\mathsf{G}_{[0, 10]}\mu_2 \wedge \mathsf{F}_{[5, 10]}\mu_3) \wedge \mathsf{G}_{[a_5, b_5]}\mu_4
```

**Requirement:** none

**Why none:** Abstract formula over unnamed predicates, used to illustrate a construction.

<details><summary>Context given to the model</summary>

```
formulas as per Definition \ref{nestedSTL}. It is straightforward to extend the results to STL tasks that are given by conjunction and/or disjunction of nested STL formulas, for instance, $\varphi=\mathsf{F}_{[0, 15]}(\mathsf{G}_{[0, 10]}\mu_1 \vee \mu_2 \mathsf{U}_{[5, 10]}\mu_3) \wedge \mathsf{G}_{[a_5, b_5]}\mu_4$. The sTLT thus is constructed for $\hat{\varphi} = \mathsf{F}_{[0, 15]}\mathsf{G}_{[2, 10]}\mu_1 \vee \mathsf{F}_{[0, 15]}(\mathsf{G}_{[0, 10]}\mu_2 \wedge \mathsf{F}_{[5, 10]}\mu_3) \wedge \mathsf{G}_{[a_5, b_5]}\mu_4$. The implementation can be done by adding an extra barrier condition corresponding to $\mathsf{G}_{[a_5, b_5]}\mu_4$ into \eqref{eq:online_syn_lth_group}. \end{remark} Now we summarize our proposed solution in the following theorem. \begin{theorem}
```

</details>

## EVAL_57  W4389667661  (iros.tex, line 102)

*STL: Surprisingly Tricky Logic (for System Validation)* (2023), licence tier: custom_or_arxiv

**Formula**

$$
\phi_1 = \mathbf{G}_{[470,491]}(z<1.69)
$$

Source:

```latex
\phi_1 = \mathbf{G}_{[470,491]}(z<1.69)
```

**Requirement:** none

**Why none:** Quoted as an example of formulas that come without a natural-language reading.

<details><summary>Context given to the model</summary>

```
and ad hoc manner for the purposes of presenting the associated paper. If we examine some of the actual outputs of these systems, as well as inputs used for plan synthesis (before ad hoc English translations) we find examples such as the following: A simple case in STL: ``$\phi = (\phi_1 \wedge \phi_2) \vee (\neg \phi_1 \wedge \phi_3), \text{where } \phi_1 = \mathbf{G}_{[470,491]}(z<1.69), \phi_2 = \mathbf{G}_{[473,490]}(v_y \geq 3.31), \text{and } \phi_3 = \mathbf{F}_{[473,491]}(y<10.54)$'' \cite{aasi2021inferring}. A more complex case encoding some of the rules for a search game in linear temporal logic (LTL): ``$\square(\neg(\bigcirc
```

</details>

## EVAL_58  W4401210599  (main.tex, line 856)

*BEACON: A Bayesian Evolutionary Approach for Counterexample Generation of Control Systems* (2024), licence tier: custom_or_arxiv

**Formula**

$$
\mathbf{G}_{[0,50]}(\neg(|h-Ref| > 0.005+0.04|Ref|)\Rightarrow \mathbf{F}_{[0,2]}\mathbf{G}_{[0,1]}(\left | h-Ref \right |\leq 0.005+0.04\left | Ref \right |))
$$

Source:

```latex
\mathbf{G}_{[0,50]}(\neg(|h-Ref| > 0.005+0.04|Ref|)\Rightarrow \mathbf{F}_{[0,2]}\mathbf{G}_{[0,1]}(\left | h-Ref \right |\leq 0.005+0.04\left | Ref \right |))
```

**Requirement:** none

**Why none:** Table of specifications with formulas only.

<details><summary>Context given to the model</summary>

```
\bottomrule \end{tabularx} \label{AT_Spec} \end{minipage} \end{tabular} \end{table*} \begin{table*}[b] \centering \caption{Neural network specifications and environmental parameters} \begin{tabularx}{\linewidth}{p{3cm} X} \toprule \textbf{Specification} & \textbf{STL specification}\\ \midrule $\varphi_{1}$ & $\mathbf{G}(h < 3.9)$\\ $\varphi_{2}$ & $\mathbf{G}_{[0,50]}(\neg(|h-Ref| > 0.005+0.04|Ref|)\Rightarrow \mathbf{F}_{[0,2]}\mathbf{G}_{[0,1]}(\left | h-Ref \right |\leq 0.005+0.04\left | Ref \right |))$\\ \end{tabularx} \begin{tabularx}{\linewidth}{p{3cm} p{1.5cm} X} \toprule \textbf{Parameter} & \textbf{Symbol} & \textbf{Range}\\ \midrule Reference & $Ref$ & $[0,3]^{8}$\\ \bottomrule \end{tabularx} \label{NN_Table} \end{table*} \subsection{Case Study
```

</details>

## EVAL_59  W4407951071  (simulations.tex, line 3)

*Decentralized Control of Multi-Agent Systems Under Acyclic Spatio-Temporal Task Dependencies* (2024), licence tier: unspecified

**Formula**

$$
\varphi_{12}= F_{[30,40]} \|\bm{p}_{12}\| \leq 5
$$

Source:

```latex
\varphi_{12}= F_{[30,40]} \|\vec{p}_{12}\| \leq 5
```

**Requirement:** none

**Why none:** Listed among task formulas in a simulation setup, with no wording of the task.

<details><summary>Context given to the model</summary>

```
distance. We select a sampling interval $\delta t =0.1s$ and communication radius $r_c=8.5$. The control constraints are $\|\vec{u}_1\| \leq 0.9$ and $|v_i|\leq 0.6\land |\omega_i|<0.15,\, \forall i=2,\ldots 7$. We then define the acyclic set of edges $\mathcal{E}_{\psi} = \{(1,2),(1,3),(2,4),(2,5),(3,6),(3,7),(1,1)\}$ with collaborative formation tasks $\varphi_{12}= F_{[30,40]} \|\vec{p}_{12}\| \leq 5, \varphi_{37}= F_{[20,30]} \|\vec{p}_{37} - [2.5,-2.5]^T\|\leq 2, \varphi_{36}= G_{[20,30]} \|\vec{p}_{37} - [-2.5,2.5]^T\|\leq 2$ and communication maintenance task $\varphi_{ij}^{comm},\; \forall (i,j)\in \mathcal{E}_{\psi}$ as per Corollary \ref{communicationc
```

</details>

## EVAL_60  W7154465483  (mitl2gta-arxiv-v2.tex, line 3556)

*TEMPORA: Efficient Verification of Metric Temporal Properties with Past in Pointwise Semantics* (2026), licence tier: custom_or_arxiv

**Formula**

$$
\mathop{\mathsf{G}\vphantom{a}}\nolimits_{[0, 10]} \mathop{\mathsf{F}\vphantom{a}}\nolimits_{[1, 2]} ( (a \wedge (\mathop{\mathsf{X}\vphantom{a}}\nolimits b) ) \vee (\neg a \wedge !(\mathop{\mathsf{X}\vphantom{a}}\nolimits b) ))
$$

Source:

```latex
\Always_{[0, 10]} \Eventually_{[1, 2]} ( (a \wedge (\Next b) ) \vee (\neg a \wedge !(\Next b) ))
```

**Requirement:** none

**Why none:** Tool benchmark table: formula and translation times.

<details><summary>Context given to the model</summary>

```
cases. \begin{table}[hbtp] \centering \resizebox{\textwidth}{!}{ \begin{tabular}{|l|l|r|r|} \hline Sl. & \multicolumn{1}{c|}{Formula} & \multicolumn{2}{|c|}{Time taken by}\\ \cline{3-4} No. & & \MightyL\ (ms) & \tool\ (ms) \\ \hline 1 & $(((((p0 \U_{[1, 2]} q1) \U_{[1, 2]} q2) \U_{[1, 2]} q3) \U_{[1, 2]} q4) \U_{[1, 2]} q5)$ & 50 & 5\\ \hline 2 & $\Always_{[0, 10]} \Eventually_{[1, 2]} ( (a \wedge (\Next b) ) \vee (\neg a \wedge !(\Next b) ))$ & 15 & 3\\ \hline 3 & $\Always_{[2, \infty)} ( (\neg request \vee \Eventually_{[4, 5]} grant))$ & 42 & 4\\ \hline 4 & $\Eventually_{[1, 2]} p1 \wedge \Eventually_{[1, 2]} p2 \wedge \Eventually_{[1, 2]} p3 \wedge \Eventually_{[1, 2]} p4 \wedge \Eventually_{[1,
```

</details>

## EVAL_61  W3113301275  (main.tex, line 855)

*Signal-Based Properties of Cyber-Physical Systems: Taxonomy and Logic-based Characterization* (2020), licence tier: restricted_cc

**Formula**

$$
\mathsf{G}_{[2,6]} (s < 3)\land\mathsf{G}_{[10,15]} (s < 3)
$$

Source:

```latex
\mathsf{G}_{[2,6]} (s < 3)\land\mathsf{G}_{[10,15]} (s < 3)
```

**Requirement:** none

**Why none:** Given as an alternative formalisation; the nearby prose defines a different property (a spike).

<details><summary>Context given to the model</summary>

```
(\protect\veryThickLine) satisfies the property whereas signal $s_2$ (\protect\thinLine) violates it. } \label{fig:DA} \end{figure} \subsubsection{Alternative formalizations} Data assertion properties like \textit{pDA} can be also expressed in \stl and \stlstar: \[ \begin{aligned} \logiclbl{STL}{\textit{pDA}} \equiv \logiclbl{STL*}{\textit{pDA}} \quad &\mathsf{G}_{[2,6]} (s < 3)\land\mathsf{G}_{[10,15]} (s < 3) \end{aligned} \] \subsection{Spike} \label{sec:bumps} A spike\footnote{A spike is also called bump, peak, or pulse in the literature.} can be informally defined as a short-lived, (relatively) large increase or decrease of the value of a signal. Such
```

</details>

## EVAL_62  W4402366853  (paper.tex, line 334)

*ECATS: Explainable-by-Design Concept-Based Anomaly Detection for Time Series* (2024), licence tier: custom_or_arxiv

**Formula**

$$
\mathcal{G}_{[0, 24]} \mathcal{F}_{[0,12]} \, \xi \le 37.26
$$

Source:

```latex
\mathcal{G}_{[0, 24]} \mathcal{F}_{[0,12]} \, \xi \le 37.26
```

**Requirement:** none

**Why none:** Learned explanation formula; the text discusses how well it separates classes, not what it requires.

<details><summary>Context given to the model</summary>

```
further discuss the results obtained with one of the seeds. Let's see some other local explanations provided by ECATS, starting from one provided for a regular trajectory. As earlier, consider the post-processed explanation given for a signal $\xi$ correctly classified as regular, which can be visualised in Figure~\ref{fig:regular1v2}: \begin{equation*} \mathcal{G}_{[0, 24]} \mathcal{F}_{[0,12]} \, \xi \le 37.26 \end{equation*} Keeping Figure~\ref{fig:dataset} at hand, this formula doesn't seem to describe any particular class since in the considered time interval most trajectories are $\le 37.26$. However, by plotting the robustness (Figure~\ref{fig:normalrob2})
```

</details>

## EVAL_63  W2092884371  (bench_encodings.tex, line 7)

*Model predictive control with signal temporal logic specifications* (2014), licence tier: custom_or_arxiv

**Formula**

$$
\varphi_3=\operatorname{\Box}_{[0,0.5]}\operatorname{\Diamond}_{[0,0.1]}(x_t^{(1)}>0.1)
$$

Source:

```latex
\f_3=\G_{[0,0.5]}\F_{[0,0.1]}(x_t^{(1)}>0.1)
```

**Requirement:** none

**Why none:** One of a bare list of benchmark formulas.

<details><summary>Context given to the model</summary>

```
We implemented the Boolean and robust encodings using the tools Breach \cite{breach} and YALMIP \cite{YALMIP}, and now present results obtained with the following formulas: \begin{itemize} \item $\f_1=\G_{[0,0.1]} x^{(1)}_t>0.1$ \item $\f_2=\G_{[0,0.1]} (x^{(1)}_t>0.1) \wedge \G_{[0,0.1]} (x^{(2)}_t<-0.5)$ \item $\f_3=\G_{[0,0.5]}\F_{[0,0.1]}(x_t^{(1)}>0.1)$ \item $\f_4=\F_{[0,0.2]} ( x^{(1)}_t>0.1 \wedge (\F_{[0,0.1]}(x_t^{(2)}>0.1)$\\ $~~~~~~~~~\wedge \F_{[0,0.1]} (x^{(3)}_t>0.1)))$ \end{itemize} In this study, we used the trivial system $\x = \u$, where $\x$ is a 3-dimensional signal (i.e. $x_t = x_t^{(1)}x_t^{(2)}x_t^{(3)}$),
```

</details>

## EVAL_64  W4410555912  (hscc_paper_ar.tex, line 456)

*Exploring Behaviors of Hybrid Systems via the Voronoi Bias over Output Signals* (2025), licence tier: custom_or_arxiv

**Formula**

$$
(\Diamond_{[0, 30]} ( y > 6)) \Rightarrow (\Box_{[0, 30]} ( y>-6\;))
$$

Source:

```latex
(\Diamond_{[0, 30]} ( y > 6)) \Rightarrow (\Box_{[0, 30]} ( y>-6\;))
```

**Requirement:** none

**Why none:** Benchmark specification mentioned by name while discussing search performance.

<details><summary>Context given to the model</summary>

```
best performing strategy overall. We already observed the reason in Section 3.2: the shape of falsifying output signals may be to complex to be effectively searched for by a single-valued feature. For example, the selection of feature space $\mathcal{F}^{y}_1$ for the SI benchmark resulted in the runs in which a counterexample to specification SI10 $(\Diamond_{[0, 30]} ( y > 6)) \Rightarrow (\Box_{[0, 30]} ( y>-6\;))$ was not generated at all, whereas for $\mathcal{F}^{y}_2$ and $\mathcal{F}^{y}_3$ were. A noticeable difference can also be observed for specifications SI11--SI12, which include these "v-shaped" signals. However, features such as $\mathcal{F}^{y}_1$
```

</details>

## EVAL_65  W3145181782  (acc21_arxiv_final.tex, line 249)

*Control Synthesis using Signal Temporal Logic Specifications with Integral and Derivative Predicates* (2021), licence tier: custom_or_arxiv

**Formula**

$$
G_{[0,5]}F_{[0,4]}x\geq0
$$

Source:

```latex
G_{[0,5]}F_{[0,4]}x\geq0
```

**Requirement:** none

**Why none:** Used to illustrate how a formula's time horizon is computed.

<details><summary>Context given to the model</summary>

```
=\max_{i \in \{1,\dots, m\}} hrz ( \varphi _{i}),\\ \phi &=G_{[t_1,t_2]}\mu\;\;\text{or}\;\;\phi =F_{[t_1,t_2]} \mu \Longrightarrow hrz(\phi) =t_2,\\ \phi &=G_{[t_1,t_2]}\varphi\;\;\text{or}\;\;\phi =F_{[t_1,t_2]} \varphi \Longrightarrow hrz(\phi) =t_2 + hrz(\varphi). \label{eq:horizon} \end{split} \end{equation} \color{black} For instance, the formula $G_{[0,5]}F_{[0,4]}x\geq0$ has a horizon of $5+4=9$, and the formula $G_{[0,5]} x\geq 0 \wedge F_{[0,4} x \geq 10$ has a horizon of $\max(5,4)=5$. \normalsize The satisfaction of specifications is indicated as either \textit{True} or \textit{False} for the most of the temporal
```

</details>
