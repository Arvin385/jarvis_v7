# Jarvis V7

The seventh version of the Jarvis Project. The goal is to create a system that reduces the number of tedious, low-skill tasks I need to do on a daily-basis.

### The differentiation of V7 is the following:

1. Dual-Client Use
    - I can use Jarvis from my Phone or my Personal Laptop.

2. Distributive LLM Compute
    - A two or three server system running simultanious agents.
    - Phone and Personal Laptop used as Classification and Execution Agents.
    - Gaming Laptop is used for a Reason/Action Loop for deep thinking.

3. Jarvis as a Proactive Agent
    - Many tasks or alerts must be completed without the initation of the user (me)
    - Includes but not limited to: Email, Canvas, and text notifications, Server Status Alerts, and fixing fatally urgent system issues (ex. server goes down--> Jarvis notices and reboots)

Note: From here on out, I will refer to my personal laptop as "xenbook" and my gaming laptop as "loq". These will also be consistent throughout the code.

## Implementation Outline

#### Processing paths:

Phone: Prompt --> Local Phone LLM classifier --simple--> Unified Memory --> Xenbook LLM generation --> Voice/Text  
                                            |                                                              ^  
                                         complex        ___________________________________________________|
                                            |           |
                                            v           |
                                        LOQ Reason/Action Loop <==> Tools



Xenbook: Prompt --> Local Xenbook LLM classifier --simple--> Unified Memory --> Xenbook LLM generation --> Voice/Text  
                                            |                                                                  ^  
                                         complex        _______________________________________________________|
                                            |           |
                                            v           |
                                        LOQ Reason/Action Loop <==> Tools


### Unified Memory System

The system will have four types of memory stored in two formats: Vector Database (embedded) and Working Session History (text). 

##### Vector Database
This stores embedded JSON items of three types:
1. Episodic Memory
2. Procedural Memory
3. Semantic Memory

##### Working Session History
This is a text-base window buffer that is injected in the LLM prompt. In the future, I am looking at creating a session main summary, foundational points, etc. to keep the model grounded.

### Reason Action Loop Design


### Tools


### Input/Output with Text and Voice